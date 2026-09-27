"""หน้าแจ้งปัญหา: ผู้ใช้พิมพ์อาการ ระบบวิเคราะห์ บันทึกตั๋ว และแสดงเลขตั๋ว"""

import pandas as pd
import streamlit as st

import db
from nlp_utils import analyze_ticket
from ui import entities_text, priority_badge

EXAMPLES = {
    "ลบข้อมูลส่วนตัว": "เน็ตช้ามาก เข้าเว็บไม่ได้ https://google.com โทร 0812345678 contact@test.com",
    "Network": "Wi-Fi หลุดบ่อยมาก เข้าเว็บไม่ได้เลย",
    "Hardware": "เปิดคอมไม่ติด ปริ้นเตอร์พิมพ์งานไม่ออก",
    "Software": "ลืมรหัสผ่าน เข้าโปรแกรมไม่ได้ ช่วยรีเซ็ตพาสเวิร์ด",
    "ตัดคำ/Stopwords": "คือว่ากล่องรับสัญญาณไฟไม่เข้าเลยครับผม",
    "NER + ด่วน": "ปริ้นเตอร์ห้อง B4-01A ใช้งานไม่ได้เลยตั้งแต่เมื่อเช้า ต้องใช้ประชุมด่วน",
}


def set_example(text: str) -> None:
    st.session_state.ticket_text = text


st.title("🎫 Smart IT Ticket Classifier")
st.write("พิมพ์อาการที่พบ ระบบจะจัดหมวดหมู่และส่งตั๋วไปยังทีมที่ดูแลให้อัตโนมัติ")

st.caption("ลองใช้ข้อความตัวอย่าง")
cols = st.columns(len(EXAMPLES))
for col, (label, text) in zip(cols, EXAMPLES.items()):
    col.button(label, on_click=set_example, args=(text,), width="stretch")

user_input = st.text_area(
    "อาการเสียหรือปัญหาที่พบ",
    key="ticket_text",
    height=120,
    placeholder="เช่น เข้าเว็บไม่ได้ เน็ตช้ามาก ห้อง B4-01A",
)

if st.button("🚀 ส่งคำร้อง", type="primary"):
    if not user_input.strip():
        st.warning("กรุณาพิมพ์อาการที่พบก่อนส่งคำร้อง")
        st.stop()

    result = analyze_ticket(user_input)
    ticket_id = db.create_ticket(result)
    st.session_state.setdefault("my_tickets", []).insert(0, ticket_id)
    st.session_state.last_result = (ticket_id, result)

if "last_result" in st.session_state:
    ticket_id, r = st.session_state.last_result
    st.divider()

    if r["needs_review"]:
        st.warning(
            f"ตั๋ว **{ticket_id}** ถูกส่งไปยัง **{r['team']}** และรอเจ้าหน้าที่ตรวจสอบ "
            f"({r['review_reason']})"
        )
    else:
        st.success(f"✅ ตั๋ว **{ticket_id}** ถูกส่งไปยัง **{r['team']}** แล้ว")
    st.caption(f"เก็บเลขตั๋ว {ticket_id} ไว้ใช้ติดตามสถานะที่หน้า \"ติดตามตั๋ว\"")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("หมวดหมู่", r["category"])
    c2.metric("หมวดย่อย", r["subcategory"])
    c3.metric("ความมั่นใจ", f"{int(r['confidence'] * 100)}%")
    c4.metric("ความเร่งด่วน", priority_badge(r["priority"]))

    st.markdown("#### ข้อมูลที่สกัดได้ (NER)")
    st.markdown(entities_text(r["entities"]))

    with st.expander("ดูขั้นตอนการประมวลผล NLP", expanded=True):
        st.markdown("**1. Regex & Cleansing — ข้อมูลที่ถูกลบ**")
        st.write(r["removed_pii"] or "ไม่พบ URL อีเมล หรือเบอร์โทร")
        st.markdown("**2. Normalization — ข้อความหลังทำความสะอาด**")
        st.code(r["cleaned_text"] or "-", language=None)
        st.markdown("**3. Tokenization & Stopwords — Cleaned Tokens**")
        st.write(r["tokens"])
        st.markdown("**4. POS Tagging — คำนาม/คำกริยาสำคัญ**")
        st.write(", ".join(f"{w} ({t})" for w, t in r["pos_keywords"]) or "-")
        st.markdown("**5. Topic Identification — คะแนนแต่ละหมวด**")
        st.bar_chart(pd.Series(r["scores"], name="คะแนน"), horizontal=True, height=180)
        st.write("คำที่ตรงกับหมวดที่เลือก:", r["matched"] or "-")
        if r["priority_hits"]:
            st.write("คำที่บ่งบอกความเร่งด่วน:", r["priority_hits"])
