"""ui.py — ส่วนแสดงผลที่หลายหน้าใช้ร่วมกัน"""

from pathlib import Path

import pandas as pd
import streamlit as st

import db
from nlp_utils import analyze_ticket

PRIORITY_ICON = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
STATUS_ICON = {"รอรับเรื่อง": "⏳", "กำลังดำเนินการ": "🔧", "เสร็จสิ้น": "✅"}
ENTITY_LABEL = {"DEVICE": "อุปกรณ์", "LOCATION": "สถานที่", "TIME": "ช่วงเวลา"}

SAMPLE_CSV = Path(__file__).parent / "test_tickets.csv"


def priority_badge(priority: str) -> str:
    return f"{PRIORITY_ICON.get(priority, '')} {priority}"


def status_badge(status: str) -> str:
    return f"{STATUS_ICON.get(status, '')} {status}"


def entities_text(entities: dict) -> str:
    parts = [f"**{ENTITY_LABEL[k]}:** {', '.join(v)}" for k, v in entities.items() if v]
    return "  \n".join(parts) if parts else "_ไม่พบอุปกรณ์ สถานที่ หรือเวลาในข้อความ_"


def status_progress(status: str) -> None:
    """แสดงสถานะเป็นขั้น ๆ ให้ผู้แจ้งเห็นว่าตั๋วอยู่ขั้นไหน"""
    idx = db.STATUSES.index(status) if status in db.STATUSES else 0
    cols = st.columns(len(db.STATUSES))
    for i, (col, name) in enumerate(zip(cols, db.STATUSES)):
        if i < idx:
            col.success(f"✔ {name}")
        elif i == idx:
            col.info(f"➤ {name}")
        else:
            col.container(border=True).caption(name)


def load_sample_tickets() -> int:
    """โหลดตั๋วตัวอย่างจาก test_tickets.csv เข้าระบบ (ใช้ตอนฐานข้อมูลว่างหลังแอป restart)"""
    df = pd.read_csv(SAMPLE_CSV)
    for text in df["text"]:
        db.create_ticket(analyze_ticket(str(text)))
    return len(df)
