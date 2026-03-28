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
                result      TEXT DEFAULT '미답변'
            )
        """)
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


def add_quiz_record(source_file: str, question: str):
    now = datetime.now(KST)
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO quiz_history (datetime, date, source_file, question, result) VALUES (?, ?, ?, ?, ?)",
            (now.isoformat(), now.strftime("%Y-%m-%d"), source_file, question, "미답변"),
        )
        conn.commit()


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
