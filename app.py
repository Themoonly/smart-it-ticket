"""
app.py — ไฟล์หลักของ Smart IT Ticket Classifier
รันด้วย: streamlit run app.py
"""

import streamlit as st

import auth
import db

st.set_page_config(page_title="Smart IT Ticket Classifier", page_icon="🎫", layout="wide")
db.init_db()

pages = {
    "สำหรับผู้แจ้ง": [
        st.Page("views/submit.py", title="แจ้งปัญหา", icon="📝", default=True),
        st.Page("views/track.py", title="ติดตามตั๋ว", icon="🔎"),
    ],
    "สำหรับทีม IT": [
        st.Page("views/team.py", title="หน้าทีมดูแล (ผู้ดูแล)", icon="🔒"),
        st.Page("views/evaluate.py", title="ทดสอบความแม่นยำ", icon="📊"),
    ],
}

nav = st.navigation(pages)

with st.sidebar:
    if auth.is_admin():
        st.success("เข้าสู่ระบบเป็นผู้ดูแล")
        st.button("ออกจากระบบ", on_click=auth.logout, width="stretch")
    st.caption("Smart IT Ticket Classifier  \nรายวิชา NLP 060233220 ภาคเรียน 1/2569")

nav.run()
