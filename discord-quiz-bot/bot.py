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
    "current_question":  None,
    "source_content":    None,
    "source_file":       None,
    "waiting_for_answer": False,
}

KST = timezone(timedelta(hours=9))

WEEKDAY_TIMES = {(9, 30), (15, 0), (19, 20), (21, 0)}
WEEKEND_TIMES = {(11, 0), (13, 38), (15, 0), (19, 0), (21, 0)}
ALL_TIMES = sorted(
    {time(hour=h, minute=m, tzinfo=KST) for h, m in WEEKDAY_TIMES | WEEKEND_TIMES}
)


# ── 학습 파일 선택 ──────────────────────────────────────────────────

def get_random_study_file() -> tuple[str, str]:
    md_map = {f.name: f for f in STUDY_DIR.glob("*.md")}
    if not md_map:
        return "", ""

    retry_files, fresh_files = get_file_candidates(set(md_map.keys()))

    if retry_files:
        candidates, tag = retry_files, "재출제(오답/부분정답)"
    elif fresh_files:
        candidates, tag = fresh_files, "신규"
    else:
        candidates, tag = set(md_map.keys()), "전체(소진)"
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


async def save_qa_to_md(question: str, answer: str):
    await asyncio.to_thread(_save_qa_sync, question, answer)


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
    filename, content = get_random_study_file()
    if not content:
        await channel.send("⚠️ 학습 자료를 찾을 수 없습니다.")
        return

    logging.info(f"학습 자료 선택: {filename}")
    state["waiting_for_answer"] = False

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

    state["current_question"]  = question
    state["source_content"]    = content
    state["source_file"]       = filename
    state["waiting_for_answer"] = True

    await channel.send(f"{question}\n\n_답변을 입력하면 채점해드립니다._")
    db.add_quiz_record(filename, question)
    logging.info("퀴즈 전송 완료")


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

    if message.content.strip() == "/status":
        await message.channel.send(build_status_message())
        return

    if message.content.strip() == "/quiz":
        await do_quiz(message.channel)
        return

    if message.content.startswith("?"):
        question_text = message.content[1:].strip()
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
        asyncio.create_task(save_qa_to_md(question_text, answer))
        return

    if not state["waiting_for_answer"]:
        return

    state["waiting_for_answer"] = False
    user_answer  = message.content
    thinking_msg = await message.channel.send("채점 중... ⏳")

    grade_prompt = f"""아래 퀴즈 문제와 사용자 답변을 채점해주세요.

=== 학습 자료 참고 ===
{state["source_content"]}
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
    db.update_last_result(state["source_file"], extract_result(result))


client.run(DISCORD_TOKEN)
