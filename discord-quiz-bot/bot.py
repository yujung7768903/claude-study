import discord
from discord.ext import tasks
import subprocess
import asyncio
import random
import os
import logging
import sys
import json
from datetime import time, datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],  # stdout으로 통일
)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
STUDY_DIR = Path.home() / "claude-study"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# 현재 출제된 문제 상태
state = {
    "current_question": None,
    "source_content": None,   # 문제를 낸 학습 자료 (채점 참고용)
    "source_file": None,
    "waiting_for_answer": False,
}

KST = timezone(timedelta(hours=9))

# 평일 (월~금): (시, 분)
WEEKDAY_TIMES = {(9, 30), (15, 0), (19, 20), (21, 0)}
# 주말 (토~일)
WEEKEND_TIMES = {(11, 0), (13, 38), (15, 0), (19, 0), (21, 0)}

# tasks.loop에는 모든 시간의 합집합을 KST로 등록
ALL_TIMES = sorted(
    {time(hour=h, minute=m, tzinfo=KST) for h, m in WEEKDAY_TIMES | WEEKEND_TIMES}
)


def get_random_study_file() -> tuple[str, str]:
    """
    파일 선택 우선순위:
    1. 오답/부분정답 파일 (다음날부터 1주 내 재출제)
    2. 1주 내 출제 이력 없는 파일
    3. 모두 소진 시 전체에서 선택
    """
    md_map = {f.name: f for f in STUDY_DIR.glob("*.md")}
    if not md_map:
        return "", ""

    retry_files, fresh_files = get_file_candidates(set(md_map.keys()))

    if retry_files:
        candidates = retry_files
        tag = "재출제(오답/부분정답)"
    elif fresh_files:
        candidates = fresh_files
        tag = "신규"
    else:
        candidates = set(md_map.keys())
        tag = "전체(소진)"
        logging.warning("출제 가능한 파일 없음, 전체에서 선택")

    chosen_name = random.choice(list(candidates))
    content = md_map[chosen_name].read_text(encoding="utf-8")
    logging.info(f"파일 선택 [{tag}]: {chosen_name} (재출제 {len(retry_files)}개, 신규 {len(fresh_files)}개)")
    return chosen_name, content[:4000]


CLAUDE_BIN = "/Users/User/.local/bin/claude"
GIT_BIN = "/opt/homebrew/bin/git"
HISTORY_FILE = Path(__file__).parent / "quiz_history.json"

DEDUP_DAYS = 7  # 중복 출제 방지 기간 (정답 기준)


# ── 학습 현황 관리 ──────────────────────────────────────────

def load_history() -> list:
    if not HISTORY_FILE.exists():
        return []
    with HISTORY_FILE.open(encoding="utf-8") as f:
        return json.load(f).get("records", [])


def save_history(records: list):
    with HISTORY_FILE.open("w", encoding="utf-8") as f:
        json.dump({"records": records}, f, ensure_ascii=False, indent=2)


def get_file_candidates(all_files: set) -> tuple[set, set]:
    """
    파일을 두 그룹으로 분류해 반환.
    - retry_files : 오답/부분정답 파일 (다음날부터 1주 내 재출제 대상)
    - fresh_files : DEDUP_DAYS 내 출제 이력 없는 파일
    """
    records = load_history()
    now = datetime.now(KST)
    today = now.date()
    cutoff = now - timedelta(days=DEDUP_DAYS)

    # 파일별 가장 최근 기록만 추출
    latest: dict[str, dict] = {}
    for r in records:
        dt = datetime.fromisoformat(r["datetime"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=KST)
        fname = r["source_file"]
        if fname not in latest or dt > latest[fname]["dt"]:
            latest[fname] = {"dt": dt, "result": r["result"]}

    retry_files: set = set()
    excluded_files: set = set()

    for fname, info in latest.items():
        if info["dt"] < cutoff:
            continue  # 오래된 기록 → 제외 대상 아님
        if info["result"] in ("오답", "부분정답", "미답변"):
            # 오늘 출제된 건 오늘 다시 안 냄 (다음날부터)
            if info["dt"].date() < today:
                retry_files.add(fname)
            else:
                excluded_files.add(fname)  # 오늘 건 오늘은 스킵
        else:
            # 정답/미확인 → DEDUP_DAYS 동안 제외
            excluded_files.add(fname)

    fresh_files = all_files - excluded_files - retry_files
    return retry_files, fresh_files


def add_quiz_record(source_file: str, question: str):
    records = load_history()
    records.append({
        "datetime": datetime.now(KST).isoformat(),
        "date": datetime.now(KST).strftime("%Y-%m-%d"),
        "source_file": source_file,
        "question": question,
        "result": "미답변",
    })
    save_history(records)


def update_last_result(source_file: str, result: str):
    """해당 파일의 가장 최근 미답변 기록을 결과로 업데이트"""
    records = load_history()
    for r in reversed(records):
        if r["source_file"] == source_file and r["result"] == "미답변":
            r["result"] = result
            break
    save_history(records)


def extract_result(grade_text: str) -> str:
    if "🔶" in grade_text or "부분정답" in grade_text:
        return "부분정답"
    if "✅" in grade_text or "정답" in grade_text:
        return "정답"
    if "❌" in grade_text or "오답" in grade_text:
        return "오답"
    return "미확인"


def build_status_message() -> str:
    records = load_history()
    now = datetime.now(KST)

    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def parse_dt(r):
        dt = datetime.fromisoformat(r["datetime"])
        return dt if dt.tzinfo else dt.replace(tzinfo=KST)

    def summarize(recs: list) -> str:
        total     = len(recs)
        correct   = sum(1 for r in recs if r["result"] == "정답")
        wrong     = sum(1 for r in recs if r["result"] == "오답")
        partial   = sum(1 for r in recs if r["result"] == "부분정답")
        unanswered = sum(1 for r in recs if r["result"] in ("미답변", "미확인"))
        answered  = correct + wrong + partial
        accuracy  = round(correct / answered * 100) if answered else 0
        bar_filled = round(accuracy / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        return (
            f"총 **{total}**문제  "
            f"✅ {correct}  ❌ {wrong}  🔶 {partial}  ⬜ {unanswered}\n"
            f"정답률 `{bar}` **{accuracy}%**"
        )

    week_recs  = [r for r in records if parse_dt(r) >= week_start]
    month_recs = [r for r in records if parse_dt(r) >= month_start]

    # 재출제 대기 중인 파일 (오답/부분정답, 오늘 이전)
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


def run_claude(prompt: str) -> str:
    result = subprocess.run(
        [CLAUDE_BIN, "-p", prompt],
        capture_output=True,
        text=True,
        cwd=str(STUDY_DIR),
    )
    if result.returncode != 0:
        return f"(오류: {result.stderr.strip()})"
    return result.stdout.strip()


def _save_qa_sync(question: str, answer: str):
    # git pull
    pull = subprocess.run(
        [GIT_BIN, "pull"],
        capture_output=True, text=True, cwd=str(STUDY_DIR),
    )
    logging.info(f"git pull: {pull.stdout.strip() or pull.stderr.strip()}")

    # 파일명용 slug 생성 (Claude에게 요청)
    slug = run_claude(
        f"다음 질문을 영어 kebab-case로 4단어 이내로 요약해줘. 결과(slug)만 출력:\n{question}"
    ).strip().lower().replace(" ", "-")

    today = datetime.now(KST).strftime("%Y%m%d")
    filename = f"{today}-{slug}.md"
    filepath = STUDY_DIR / filename

    # md 내용 생성 (기존 파일 형식에 맞게 Claude에게 요청)
    md_content = run_claude(
        f"""다음 Q&A를 기존 학습 노트 형식에 맞게 마크다운으로 정리해줘.
형식 규칙:
- 첫 줄은 # 제목 (질문 기반)
- ## 개념 설명, ### 소제목 등 계층 구조 활용
- 코드가 있으면 코드블록 사용
- --- 구분선 적절히 사용
- 핵심 내용만 간결하게

질문: {question}

답변: {answer}"""
    )

    filepath.write_text(md_content, encoding="utf-8")
    logging.info(f"md 저장 완료: {filename}")


async def save_qa_to_md(question: str, answer: str):
    await asyncio.to_thread(_save_qa_sync, question, answer)


@client.event
async def on_ready():
    print(f"✅ {client.user} 로 접속 완료")
    send_quiz.start()


async def do_quiz(channel):
    """퀴즈 1문제를 출제해 channel로 전송. 스케줄 및 /quiz 공용."""
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

    logging.info("claude -p 로 문제 생성 중...")
    question = await asyncio.to_thread(run_claude, prompt)
    logging.info(f"문제 생성 완료: {question[:50]}...")

    state["current_question"] = question
    state["source_content"] = content
    state["source_file"] = filename
    state["waiting_for_answer"] = True

    await channel.send(f"{question}\n\n_답변을 입력하면 채점해드립니다._")
    add_quiz_record(filename, question)
    logging.info("문제 전송 완료")


@tasks.loop(time=ALL_TIMES)
async def send_quiz():
    now = datetime.now(KST)
    is_weekend = now.weekday() >= 5
    schedule = WEEKEND_TIMES if is_weekend else WEEKDAY_TIMES
    logging.info(f"send_quiz 호출됨: {now.strftime('%H:%M')} {'주말' if is_weekend else '평일'} 스케줄={schedule}")

    if (now.hour, now.minute) not in schedule:
        logging.info("현재 시각은 스케줄에 없음, 스킵")
        return

    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        logging.error(f"채널을 찾을 수 없음: {CHANNEL_ID}")
        return

    logging.info(f"채널 확인: {channel.name}")
    await do_quiz(channel)


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.id != CHANNEL_ID:
        return

    # /status: 학습 현황 요약
    if message.content.strip() == "/status":
        await message.channel.send(build_status_message())
        return

    # /quiz: 즉시 문제 출제
    if message.content.strip() == "/quiz":
        await do_quiz(message.channel)
        return

    # ? prefix: 자유 질문 모드
    if message.content.startswith("?"):
        question_text = message.content[1:].strip()
        if not question_text:
            return
        thinking_msg = await message.channel.send("답변 생성 중... ⏳")
        answer = await asyncio.to_thread(run_claude, question_text)
        await thinking_msg.delete()
        await message.channel.send(answer)
        # 답변 후 백그라운드에서 md 파일 저장
        asyncio.create_task(save_qa_to_md(question_text, answer))
        return

    if not state["waiting_for_answer"]:
        return

    state["waiting_for_answer"] = False
    user_answer = message.content

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

    result = await asyncio.to_thread(run_claude, grade_prompt)

    await thinking_msg.delete()
    await message.channel.send(result)

    update_last_result(state["source_file"], extract_result(result))


client.run(DISCORD_TOKEN)
