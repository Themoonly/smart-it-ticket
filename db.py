"""
db.py
เก็บตั๋วด้วย SQLite เพื่อให้ทุกหน้า (ผู้แจ้ง / ทีมดูแล) เห็นข้อมูลชุดเดียวกัน

หมายเหตุ: บน Streamlit Community Cloud ไฟล์ฐานข้อมูลจะถูกล้างเมื่อแอป restart หรือ redeploy
เหมาะสำหรับเดโม ถ้าใช้งานจริงควรเปลี่ยนไปใช้ฐานข้อมูลภายนอก เช่น Supabase หรือ Google Sheets
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DB_PATH = Path(__file__).parent / "data" / "tickets.db"
TZ = ZoneInfo("Asia/Bangkok")

STATUSES = ["รอรับเรื่อง", "กำลังดำเนินการ", "เสร็จสิ้น"]


def _now() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_text        TEXT NOT NULL,
                tokens          TEXT,
                category        TEXT,
                subcategory     TEXT,
                team            TEXT,
                original_team   TEXT,
                confidence      REAL,
                priority        TEXT,
                entities        TEXT,
                needs_review    INTEGER DEFAULT 0,
                review_reason   TEXT,
                status          TEXT DEFAULT 'รอรับเรื่อง',
                reassigned      INTEGER DEFAULT 0,
                note            TEXT DEFAULT '',
                created_at      TEXT,
                updated_at      TEXT
            )
            """
        )


def format_ticket_id(num: int) -> str:
    return f"TK-{num:04d}"


def parse_ticket_id(text: str) -> int | None:
    """รับได้ทั้ง 'TK-0042', 'tk42', '42'"""
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None


def create_ticket(result: dict) -> str:
    now = _now()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO tickets (raw_text, tokens, category, subcategory, team, original_team,
                                 confidence, priority, entities, needs_review, review_reason,
                                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result["raw_text"],
                json.dumps(result["tokens"], ensure_ascii=False),
                result["category"],
                result["subcategory"],
                result["team"],
                result["team"],
                result["confidence"],
                result["priority"],
                json.dumps(result["entities"], ensure_ascii=False),
                int(result["needs_review"]),
                result["review_reason"],
                now,
                now,
            ),
        )
        return format_ticket_id(cur.lastrowid)


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["ticket_id"] = format_ticket_id(d["id"])
    d["tokens"] = json.loads(d["tokens"] or "[]")
    d["entities"] = json.loads(d["entities"] or "{}")
    d["needs_review"] = bool(d["needs_review"])
    d["reassigned"] = bool(d["reassigned"])
    return d


def get_ticket(num: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (num,)).fetchone()
    return _row_to_dict(row) if row else None


def get_tickets(ids: list[int]) -> list[dict]:
    """ดึงตั๋วหลายใบในคิวรีเดียว เรียงแบบเดียวกับ list_tickets (ยังไม่เสร็จ → priority → ใหม่สุดก่อน)"""
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    sql = f"""SELECT * FROM tickets WHERE id IN ({placeholders})
              ORDER BY CASE status WHEN 'เสร็จสิ้น' THEN 1 ELSE 0 END,
                       CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END,
                       id DESC"""
    with _connect() as conn:
        rows = conn.execute(sql, ids).fetchall()
    return [_row_to_dict(r) for r in rows]


def list_tickets(team: str | None = None, review_only: bool = False) -> list[dict]:
    sql, params = "SELECT * FROM tickets WHERE 1=1", []
    if team:
        sql += " AND team = ?"
        params.append(team)
    if review_only:
        sql += " AND needs_review = 1 AND status != 'เสร็จสิ้น'"
    sql += """ ORDER BY CASE status WHEN 'เสร็จสิ้น' THEN 1 ELSE 0 END,
                        CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END,
                        id DESC"""
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def update_status(num: int, status: str, note: str = "") -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE tickets SET status = ?, note = ?, updated_at = ? WHERE id = ?",
            (status, note, _now(), num),
        )


def reassign_ticket(num: int, new_team: str, new_category: str) -> None:
    """ช่างแจ้งว่าส่งผิดทีม: ย้ายทีม, ปิดสถานะ review, และเก็บทีมเดิมไว้วัดความแม่นยำ"""
    with _connect() as conn:
        conn.execute(
            """
            UPDATE tickets
            SET team = ?, category = ?,
                reassigned = CASE WHEN ? != original_team THEN 1 ELSE 0 END,
                needs_review = 0, status = 'รอรับเรื่อง', updated_at = ?
            WHERE id = ?
            """,
            (new_team, new_category, new_team, _now(), num),
        )


def confirm_team(num: int) -> None:
    """เจ้าหน้าที่ Human Review ยืนยันว่าทีมที่ระบบเลือกถูกต้อง"""
    with _connect() as conn:
        conn.execute(
            "UPDATE tickets SET needs_review = 0, updated_at = ? WHERE id = ?", (_now(), num)
        )


def get_stats() -> dict:
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        auto = conn.execute("SELECT COUNT(*) FROM tickets WHERE original_team != 'Frontline Helpdesk'").fetchone()[0]
        review = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE needs_review = 1 AND status != 'เสร็จสิ้น'"
        ).fetchone()[0]
        reassigned = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE reassigned = 1 AND original_team != 'Frontline Helpdesk'"
        ).fetchone()[0]
        by_team = dict(conn.execute("SELECT team, COUNT(*) FROM tickets GROUP BY team").fetchall())
        by_status = dict(conn.execute("SELECT status, COUNT(*) FROM tickets GROUP BY status").fetchall())
    routing_accuracy = (auto - reassigned) / auto if auto else None
    return {
        "total": total,
        "auto_routed": auto,
        "pending_review": review,
        "reassigned": reassigned,
        "routing_accuracy": routing_accuracy,
        "by_team": by_team,
        "by_status": by_status,
    }


def get_new_counts() -> dict[str, int]:
    """จำนวนตั๋วสถานะ 'รอรับเรื่อง' แยกตามทีม ใช้แสดงตัวเลขตั๋วใหม่ในหน้าทีมดูแล"""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT team, COUNT(*) FROM tickets WHERE status = ? GROUP BY team", (STATUSES[0],)
        ).fetchall()
    return dict(rows)


def clear_all() -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM tickets")
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'tickets'")
