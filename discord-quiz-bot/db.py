import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent / "data")))
DB_PATH  = DATA_DIR / "bot.db"


def _get_conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quiz_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                datetime    TEXT NOT NULL,
                date        TEXT NOT NULL,
                source_file TEXT NOT NULL,
                question    TEXT NOT NULL,
                result      TEXT DEFAULT '미답변',
                deleted     INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS custom_questions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                question   TEXT NOT NULL,
                deleted    INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        # 기존 quiz_history에 deleted 컬럼 없으면 추가
        try:
            conn.execute("ALTER TABLE quiz_history ADD COLUMN deleted INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        conn.commit()


def migrate_from_json(json_path: Path):
    """quiz_history.json → SQLite 마이그레이션 (최초 1회만 실행)"""
    if not json_path.exists():
        return
    with _get_conn() as conn:
        if conn.execute("SELECT COUNT(*) FROM quiz_history").fetchone()[0] > 0:
            return  # 이미 마이그레이션 완료
        with json_path.open(encoding="utf-8") as f:
            records = json.load(f).get("records", [])
        for r in records:
            conn.execute(
                "INSERT INTO quiz_history (datetime, date, source_file, question, result) VALUES (?, ?, ?, ?, ?)",
                (r["datetime"], r["date"], r["source_file"], r["question"], r["result"]),
            )
        conn.commit()


def load_history() -> list:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM quiz_history ORDER BY datetime").fetchall()
        return [dict(r) for r in rows]


def add_quiz_record(source_file: str, question: str) -> int:
    now = datetime.now(KST)
    with _get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO quiz_history (datetime, date, source_file, question, result) VALUES (?, ?, ?, ?, ?)",
            (now.isoformat(), now.strftime("%Y-%m-%d"), source_file, question, "미답변"),
        )
        conn.commit()
        return cursor.lastrowid


def update_last_result(source_file: str, result: str):
    with _get_conn() as conn:
        conn.execute(
            """
            UPDATE quiz_history SET result = ?
            WHERE id = (
                SELECT id FROM quiz_history
                WHERE source_file = ? AND result = '미답변'
                ORDER BY datetime DESC LIMIT 1
            )
            """,
            (result, source_file),
        )
        conn.commit()


def update_result_by_id(quiz_id: int, result: str):
    with _get_conn() as conn:
        conn.execute(
            "UPDATE quiz_history SET result = ? WHERE id = ?",
            (result, quiz_id),
        )
        conn.commit()


def add_custom_question(question: str) -> int:
    now = datetime.now(KST)
    with _get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO custom_questions (question, deleted, created_at) VALUES (?, 0, ?)",
            (question, now.isoformat()),
        )
        conn.commit()
        return cursor.lastrowid


def get_active_custom_questions() -> list:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM custom_questions WHERE deleted = 0"
        ).fetchall()
        return [dict(r) for r in rows]


def delete_quiz(quiz_id: int) -> bool:
    """quiz_history 레코드를 deleted=1로 마킹. custom question이면 함께 삭제. 존재 여부 반환."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT source_file FROM quiz_history WHERE id = ?", (quiz_id,)
        ).fetchone()
        if not row:
            return False
        conn.execute("UPDATE quiz_history SET deleted = 1 WHERE id = ?", (quiz_id,))
        source_file = row["source_file"]
        if source_file.startswith("custom:"):
            custom_id = int(source_file.split(":")[1])
            conn.execute("UPDATE custom_questions SET deleted = 1 WHERE id = ?", (custom_id,))
        conn.commit()
        return True
