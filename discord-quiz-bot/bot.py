import discord
from discord.ext import tasks
import subprocess
import asyncio
import random
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import time, datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv

import db
from claude_client import call_claude, SONNET, HAIKU

load_dotenv()

# ── 경로 설정 (환경변수로 Docker / 로컬 모두 동작) ─────────────────
STUDY_DIR  = Path(os.getenv("STUDY_DIR",  str(Path.home() / "claude-study")))
DATA_DIR   = Path(os.getenv("DATA_DIR",   str(Path(__file__).parent / "data")))
LOG_DIR    = Path(os.getenv("LOG_DIR",    str(Path(__file__).parent / "logs")))
GIT_BIN    = os.getenv("GIT_BIN", "git")          # 로컬: /opt/homebrew/bin/git, 서버: git

LOG_DIR.mkdir(parents=True, exist_ok=True)

_log_handler = TimedRotatingFileHandler(
    LOG_DIR / "bot.log",
    when="midnight",
    backupCount=1,
    encoding="utf-8",
)
_log_handler.suffix = "%Y-%m-%d"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[_log_handler, logging.StreamHandler()],
)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID    = int(os.getenv("CHANNEL_ID"))
GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO   = os.getenv("GITHUB_REPO", "yujung7768903/claude-study")

# DB 초기화 + JSON 마이그레이션 (최초 1회)
db.init_db()
db.migrate_from_json(Path(__file__).parent / "quiz_history.json")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

state = {
    "current_question":   None,
    "source_content":     None,
    "source_file":        None,
    "waiting_for_answer": False,
    "current_quiz_id":    None,
    "reminder_task":      None,
}

KST = timezone(timedelta(hours=9))

WEEKDAY_TIMES = {(9, 30), (15, 0), (19, 20), (21, 0)}
WEEKEND_TIMES = {(11, 0), (13, 38), (15, 0), (19, 0), (21, 0)}
ALL_TIMES = sorted(
    {time(hour=h, minute=m, tzinfo=KST) for h, m in WEEKDAY_TIMES | WEEKEND_TIMES}
)


# ── 학습 파일 선택 ──────────────────────────────────────────────────

def get_random_study_file() -> tuple[str, str]:
    md_map = {f.name: f for f in STUDY_DIR.rglob("*.md")}
    if not md_map:
        return "", ""

    current_files = set(md_map.keys())
    retry_files, fresh_files = get_file_candidates(current_files)

    # DB에 기록된 구 파일명이 현재 파일 목록에 없을 수 있으므로 필터링
    retry_files &= current_files
    fresh_files &= current_files

    if retry_files:
        candidates, tag = retry_files, "재출제(오답/부분정답)"
    elif fresh_files:
        candidates, tag = fresh_files, "신규"
    else:
        candidates, tag = current_files, "전체(소진)"
        logging.warning("출제 가능한 파일 없음, 전체에서 선택")

    chosen_name = random.choice(list(candidates))
    content = md_map[chosen_name].read_text(encoding="utf-8")
    logging.info(f"파일 선택 [{tag}]: {chosen_name} (재출제 {len(retry_files)}개, 신규 {len(fresh_files)}개)")
    return chosen_name, content[:4000]


def get_file_candidates(all_files: set) -> tuple[set, set]:
    records = db.load_history()
    now     = datetime.now(KST)
    today   = now.date()
    cutoff  = now - timedelta(days=7)

    latest: dict[str, dict] = {}
    for r in records:
        dt = datetime.fromisoformat(r["datetime"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=KST)
        fname = r["source_file"]
        if fname not in latest or dt > latest[fname]["dt"]:
            latest[fname] = {"dt": dt, "result": r["result"]}

    retry_files: set   = set()
    excluded_files: set = set()

    for fname, info in latest.items():
        if info["dt"] < cutoff:
            continue
        if info["result"] in ("오답", "부분정답", "미답변"):
            if info["dt"].date() < today:
                retry_files.add(fname)
            else:
                excluded_files.add(fname)
        else:
            excluded_files.add(fname)

    fresh_files = all_files - excluded_files - retry_files
    return retry_files, fresh_files


def extract_result(grade_text: str) -> str:
    if "🔶" in grade_text or "부분정답" in grade_text:
        return "부분정답"
    if "✅" in grade_text or "정답" in grade_text:
        return "정답"
    if "❌" in grade_text or "오답" in grade_text:
        return "오답"
    return "미확인"


def build_status_message() -> str:
    records = db.load_history()
    now = datetime.now(KST)

    week_start  = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def parse_dt(r):
        dt = datetime.fromisoformat(r["datetime"])
        return dt if dt.tzinfo else dt.replace(tzinfo=KST)

    def summarize(recs: list) -> str:
        total      = len(recs)
        correct    = sum(1 for r in recs if r["result"] == "정답")
        wrong      = sum(1 for r in recs if r["result"] == "오답")
        partial    = sum(1 for r in recs if r["result"] == "부분정답")
        unanswered = sum(1 for r in recs if r["result"] in ("미답변", "미확인"))
        answered   = correct + wrong + partial
        accuracy   = round(correct / answered * 100) if answered else 0
        bar_filled = round(accuracy / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        return (
            f"총 **{total}**문제  "
            f"✅ {correct}  ❌ {wrong}  🔶 {partial}  ⬜ {unanswered}\n"
            f"정답률 `{bar}` **{accuracy}%**"
        )

    week_recs  = [r for r in records if parse_dt(r) >= week_start]
    month_recs = [r for r in records if parse_dt(r) >= month_start]

    today = now.date()
    latest: dict[str, dict] = {}
    for r in records:
        dt = parse_dt(r)
        fname = r["source_file"]
        if fname not in latest or dt > latest[fname]["dt"]:
            latest[fname] = {"dt": dt, "result": r["result"]}

    retry_pending = [
        fname for fname, info in latest.items()
        if info["result"] in ("오답", "부분정답") and info["dt"].date() < today
    ]

    lines = ["📊 **학습 현황**", ""]
    lines += ["**📅 이번 주**", summarize(week_recs), ""]
    lines += ["**🗓 이번 달**", summarize(month_recs), ""]
    if retry_pending:
        topics = "\n".join(f"  • `{f}`" for f in retry_pending[:10])
        lines += [f"**🔁 재출제 대기** ({len(retry_pending)}개)", topics]
    else:
        lines.append("**🔁 재출제 대기**: 없음")

    return "\n".join(lines)


# ── Claude 호출 ─────────────────────────────────────────────────────

async def send_long_message(channel, text: str, limit: int = 2000):
    lines = text.split("\n")
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 > limit:
            await channel.send(chunk)
            chunk = line + "\n"
        else:
            chunk += line + "\n"
    if chunk.strip():
        await channel.send(chunk)


def _save_qa_sync(question: str, answer: str):
    subprocess.run([GIT_BIN, "pull"], capture_output=True, text=True, cwd=str(STUDY_DIR))

    # slug 생성: 단순 작업 → Haiku
    slug = call_claude(
        f"다음 질문을 영어 kebab-case로 4단어 이내로 요약해줘. 결과(slug)만 출력:\n{question}",
        model=HAIKU,
        max_tokens=32,
    ).strip().lower().replace(" ", "-")
    # 경로 탈출 방지
    slug = "".join(c for c in slug if c.isalnum() or c == "-")[:60]

    today    = datetime.now(KST).strftime("%Y%m%d")
    filename = f"{today}-{slug}.md"
    filepath = (STUDY_DIR / filename).resolve()

    # 경로 탈출 검증
    if not str(filepath).startswith(str(STUDY_DIR.resolve())):
        logging.error(f"경로 탈출 시도 차단: {filename}")
        return

    # md 내용 생성: 품질 중요 → Sonnet
    md_content = call_claude(
        f"""다음 Q&A를 기존 학습 노트 형식에 맞게 마크다운으로 정리해줘.
형식 규칙:
- 첫 줄은 # 제목 (질문 기반)
- ## 개념 설명, ### 소제목 등 계층 구조 활용
- 코드가 있으면 코드블록 사용
- --- 구분선 적절히 사용
- 핵심 내용만 간결하게

질문: {question}

답변: {answer}""",
        model=SONNET,
    )

    filepath.write_text(md_content, encoding="utf-8")
    logging.info(f"md 저장 완료: {filename}")

    # 서버 환경에서만 push (GITHUB_TOKEN 있을 때)
    if GITHUB_TOKEN:
        repo_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
        subprocess.run([GIT_BIN, "config", "user.email", "bot@assistant"], cwd=str(STUDY_DIR))
        subprocess.run([GIT_BIN, "config", "user.name", "Assistant Bot"], cwd=str(STUDY_DIR))
        subprocess.run([GIT_BIN, "add", filename], cwd=str(STUDY_DIR))
        subprocess.run([GIT_BIN, "commit", "-m", f"study: add {filename}"], cwd=str(STUDY_DIR))
        subprocess.run([GIT_BIN, "push", repo_url, "main"],
                       capture_output=True, cwd=str(STUDY_DIR))
        logging.info("study note push 완료")

    return filename


async def save_qa_to_md(question: str, answer: str) -> str:
    return await asyncio.to_thread(_save_qa_sync, question, answer)


# ── 리마인더 ─────────────────────────────────────────────────────────

async def reminder_loop(channel, quiz_id: int):
    await asyncio.sleep(600)  # 10분
    if state["waiting_for_answer"] and state["current_quiz_id"] == quiz_id:
        await channel.send(f"⏰ 아직 `#{quiz_id}` 문제를 풀지 않으셨네요! 도전해보세요.")
    else:
        return

    await asyncio.sleep(600)  # 20분
    if state["waiting_for_answer"] and state["current_quiz_id"] == quiz_id:
        await channel.send(f"⏰ 20분이 지났습니다! `#{quiz_id}` 아직 도전 중이신가요?")
    else:
        return

    await asyncio.sleep(600)  # 30분
    if state["waiting_for_answer"] and state["current_quiz_id"] == quiz_id:
        await channel.send(
            f"⏰ 30분이 지났습니다! `#{quiz_id}` 아직 답변하지 않으셨네요.\n"
            f"정답을 보시겠습니까? `/answer` 를 입력하면 정답을 확인할 수 있습니다."
        )


def _cancel_reminder():
    if state["reminder_task"] and not state["reminder_task"].done():
        state["reminder_task"].cancel()
    state["reminder_task"] = None


# ── 백업 (주 1회, 매주 일요일 새벽 3시) ────────────────────────────

def _run_backup():
    import shutil
    if not GITHUB_TOKEN:
        logging.warning("GITHUB_TOKEN 없음, 백업 건너뜀")
        return

    backup_dir = STUDY_DIR / "discord-quiz-bot" / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    db_src = DATA_DIR / "bot.db"

    if not db_src.exists():
        logging.warning("bot.db 없음, 백업 건너뜀")
        return

    shutil.copy(db_src, backup_dir / "bot.db")
    logging.info("bot.db 복사 완료")

    repo_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
    subprocess.run([GIT_BIN, "config", "user.email", "bot@assistant"], cwd=str(STUDY_DIR))
    subprocess.run([GIT_BIN, "config", "user.name", "Assistant Bot"], cwd=str(STUDY_DIR))
    subprocess.run([GIT_BIN, "add", "discord-quiz-bot/backup/bot.db"], cwd=str(STUDY_DIR))
    result = subprocess.run(
        [GIT_BIN, "commit", "-m", f"backup: weekly db {datetime.now(KST).strftime('%Y-%m-%d')}"],
        capture_output=True, text=True, cwd=str(STUDY_DIR),
    )
    if "nothing to commit" in result.stdout:
        logging.info("백업: 변경사항 없음")
        return
    subprocess.run([GIT_BIN, "push", repo_url, "main"],
                   capture_output=True, cwd=str(STUDY_DIR))
    logging.info("주간 DB 백업 push 완료")


@tasks.loop(time=time(hour=3, minute=0, tzinfo=KST))
async def weekly_backup():
    if datetime.now(KST).weekday() != 6:  # 일요일
        return
    logging.info("주간 백업 시작")
    await asyncio.to_thread(_run_backup)


# ── 스케줄 퀴즈 ─────────────────────────────────────────────────────

@tasks.loop(time=time(hour=22, minute=0, tzinfo=KST))
async def send_weekly_status():
    if datetime.now(KST).weekday() != 6:
        return
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(build_status_message())
        logging.info("주간 학습 현황 전송 완료")


@client.event
async def on_ready():
    logging.info(f"✅ {client.user} 로 접속 완료")
    if not send_quiz.is_running():
        send_quiz.start()
    if not send_weekly_status.is_running():
        send_weekly_status.start()
    if not weekly_backup.is_running():
        weekly_backup.start()


async def do_quiz(channel):
    _cancel_reminder()

    state["waiting_for_answer"] = False

    # 커스텀 문제 vs 파일 기반 문제 선택
    custom_qs = db.get_active_custom_questions()
    use_custom = bool(custom_qs) and random.random() < 0.3

    if use_custom:
        cq = random.choice(custom_qs)
        question     = cq["question"]
        source_file  = f"custom:{cq['id']}"
        source_content = ""
        logging.info(f"커스텀 문제 선택: #{cq['id']}")
    else:
        filename, content = get_random_study_file()
        if not content:
            await channel.send("⚠️ 학습 자료를 찾을 수 없습니다.")
            return

        logging.info(f"학습 자료 선택: {filename}")

        prompt = f"""아래 학습 자료를 읽고 복습 퀴즈 문제 1개를 출제해주세요.

=== 학습 자료: {filename} ===
{content}
=== 끝 ===

규칙:
- 학습 자료의 핵심 개념을 묻는 문제
- 단답형 또는 짧은 서술형
- 정답은 절대 포함하지 말 것
- 아래 형식으로만 출력 (다른 텍스트 없이):

📌 **[주제]**
❓ **문제**: (문제 내용)
💡 **힌트**: (선택사항, 불필요하면 생략)"""

        logging.info("퀴즈 생성 중 (Sonnet)...")
        question = await asyncio.to_thread(call_claude, prompt, SONNET)
        logging.info(f"퀴즈 생성 완료: {question[:50]}...")

        source_file    = filename
        source_content = content

    quiz_id = db.add_quiz_record(source_file, question)

    state["current_question"]   = question
    state["source_content"]     = source_content
    state["source_file"]        = source_file
    state["waiting_for_answer"] = True
    state["current_quiz_id"]    = quiz_id

    await channel.send(f"{question}\n\n_답변을 입력하면 채점해드립니다._ | 🆔 `#{quiz_id}`")
    state["reminder_task"] = asyncio.create_task(reminder_loop(channel, quiz_id))
    logging.info(f"퀴즈 전송 완료 (#{quiz_id})")


@tasks.loop(time=ALL_TIMES)
async def send_quiz():
    now        = datetime.now(KST)
    is_weekend = now.weekday() >= 5
    schedule   = WEEKEND_TIMES if is_weekend else WEEKDAY_TIMES
    logging.info(f"send_quiz 호출: {now.strftime('%H:%M')} {'주말' if is_weekend else '평일'}")

    if (now.hour, now.minute) not in schedule:
        logging.info("스케줄 없음, 스킵")
        return

    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        logging.error(f"채널 없음: {CHANNEL_ID}")
        return

    await do_quiz(channel)


# ── 메시지 핸들러 ────────────────────────────────────────────────────

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.id != CHANNEL_ID:
        return

    content = message.content.strip()

    if content == "/status":
        await message.channel.send(build_status_message())
        return

    if content == "/quiz":
        await do_quiz(message.channel)
        return

    if content == "/answer":
        if not state["waiting_for_answer"] or not state["current_quiz_id"]:
            await message.channel.send("현재 진행 중인 문제가 없습니다.")
            return
        thinking_msg = await message.channel.send("정답 생성 중... ⏳")
        answer_prompt = f"""다음 문제의 정답과 해설을 알려주세요.

문제:
{state["current_question"]}

{f"참고 자료:{chr(10)}{state['source_content']}" if state["source_content"] else ""}

아래 형식으로 출력해주세요:

**정답**: (핵심 답변)
**해설**: (간결한 설명)"""
        answer = await asyncio.to_thread(call_claude, answer_prompt, SONNET)
        await thinking_msg.delete()
        await send_long_message(message.channel, f"📖 **`#{state['current_quiz_id']}` 정답 공개**\n\n{answer}")
        db.update_result_by_id(state["current_quiz_id"], "정답확인")
        _cancel_reminder()
        state["waiting_for_answer"] = False
        return

    if content.startswith("/add "):
        question_text = content[5:].strip()
        if not question_text:
            await message.channel.send("문제 내용을 입력해주세요. 예: `/add 질문 내용`")
            return
        custom_id = db.add_custom_question(question_text)
        await message.channel.send(f"✅ 문제가 추가되었습니다. (커스텀 문제 ID: `#{custom_id}`에서 출제 예정)")
        logging.info(f"커스텀 문제 추가: custom_id={custom_id}")
        return

    if content.startswith("/delete "):
        id_str = content[8:].strip().lstrip("#")
        if not id_str.isdigit():
            await message.channel.send("올바른 문제 ID를 입력해주세요. 예: `/delete 42`")
            return
        quiz_id = int(id_str)
        success = db.delete_quiz(quiz_id)
        if success:
            await message.channel.send(f"🗑️ `#{quiz_id}` 문제가 삭제되었습니다. 더 이상 출제되지 않습니다.")
            logging.info(f"문제 삭제: quiz_id={quiz_id}")
        else:
            await message.channel.send(f"❌ `#{quiz_id}` 문제를 찾을 수 없습니다.")
        return

    if content.startswith("??"):
        question_text = content[2:].strip()
        if not question_text:
            return
        thinking_msg = await message.channel.send("답변 생성 중... ⏳")

        # 답변: 품질 중요 → Sonnet
        answer = await asyncio.to_thread(call_claude, question_text, SONNET)

        # 요약: 단순 작업 → Haiku
        summary_prompt = f"""다음 Q&A를 1000자 이내로 핵심만 요약해줘.
마크다운 형식을 유지하고, 마지막 줄에 추가:
_자세한 내용은 학습 자료에 저장됩니다._

질문: {question_text}
답변: {answer}"""
        summary = await asyncio.to_thread(call_claude, summary_prompt, HAIKU)

        await thinking_msg.delete()
        await message.channel.send(summary)

        filename = await save_qa_to_md(question_text, answer)
        if filename:
            await message.channel.send(f"📝 학습 자료 저장됨: `{filename}`")
        return

    if content.startswith("?"):
        question_text = content[1:].strip()
        if not question_text:
            return
        thinking_msg = await message.channel.send("답변 생성 중... ⏳")

        answer = await asyncio.to_thread(call_claude, question_text, SONNET)

        summary_prompt = f"""다음 Q&A를 1000자 이내로 핵심만 요약해줘.
마크다운 형식을 유지해줘.

질문: {question_text}
답변: {answer}"""
        summary = await asyncio.to_thread(call_claude, summary_prompt, HAIKU)

        await thinking_msg.delete()
        await message.channel.send(summary)
        return

    if not state["waiting_for_answer"]:
        return

    state["waiting_for_answer"] = False
    _cancel_reminder()

    user_answer  = message.content
    thinking_msg = await message.channel.send("채점 중... ⏳")

    grade_prompt = f"""아래 퀴즈 문제와 사용자 답변을 채점해주세요.

=== 학습 자료 참고 ===
{state["source_content"] or "커스텀 문제 (참고 자료 없음)"}
=== 끝 ===

문제:
{state["current_question"]}

사용자 답변: {user_answer}

아래 형식으로 채점 결과를 출력해주세요 (다른 텍스트 없이):

**채점**: ✅ 정답 / ❌ 오답 / 🔶 부분정답
**해설**: (맞고 틀린 이유를 간결하게)
**모범 답안**: (정확한 답변)"""

    result = await asyncio.to_thread(call_claude, grade_prompt, SONNET)

    await thinking_msg.delete()
    await send_long_message(message.channel, result)
    db.update_result_by_id(state["current_quiz_id"], extract_result(result))


client.run(DISCORD_TOKEN)
