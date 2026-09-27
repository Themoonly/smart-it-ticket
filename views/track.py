"""หน้าติดตามตั๋ว: ผู้แจ้งกรอกเลขตั๋วเพื่อดูว่าส่งไปทีมไหนและสถานะล่าสุด"""

import streamlit as st

import db
from ui import entities_text, priority_badge, status_progress

st.title("🔎 ติดตามตั๋ว")
st.write("กรอกเลขตั๋วเพื่อดูว่าคำร้องของคุณถูกส่งไปทีมไหน และตอนนี้อยู่ในขั้นตอนใด")

my_tickets = st.session_state.get("my_tickets", [])
if my_tickets:
    st.caption("ตั๋วที่คุณส่งในรอบนี้")
    cols = st.columns(min(len(my_tickets), 6))
    for col, tid in zip(cols, my_tickets[:6]):
        col.button(tid, width="stretch", on_click=st.session_state.__setitem__, args=("track_input", tid))

query = st.text_input("เลขตั๋ว", key="track_input", placeholder="เช่น TK-0001")

if query:
    num = db.parse_ticket_id(query)
    ticket = db.get_ticket(num) if num else None

    if not ticket:
        st.error(f"ไม่พบตั๋ว \"{query}\" ตรวจสอบเลขตั๋วอีกครั้ง หรือแจ้งปัญหาใหม่ที่หน้า \"แจ้งปัญหา\"")
        st.stop()

    st.subheader(ticket["ticket_id"])
    st.markdown(f"> {ticket['raw_text']}")

    st.markdown("#### สถานะ")
    status_progress(ticket["status"])

    c1, c2, c3 = st.columns(3)
    c1.metric("ทีมที่ดูแล", ticket["team"])
    c2.metric("หมวดหมู่", f"{ticket['category']}")
    c3.metric("ความเร่งด่วน", priority_badge(ticket["priority"]))

    if ticket["reassigned"]:
        st.info(f"ตั๋วนี้ถูกย้ายจาก {ticket['original_team']} มายัง {ticket['team']} โดยเจ้าหน้าที่")
    elif ticket["needs_review"]:
        st.warning("ตั๋วนี้รอเจ้าหน้าที่ตรวจสอบก่อนส่งต่อ เพราะระบบยังไม่มั่นใจในหมวดหมู่")

    if ticket["note"]:
        st.markdown(f"**ข้อความจากทีมดูแล:** {ticket['note']}")

    st.markdown(entities_text(ticket["entities"]))
    st.caption(f"แจ้งเมื่อ {ticket['created_at']} · อัปเดตล่าสุด {ticket['updated_at']}")
