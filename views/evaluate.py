"""หน้าทดสอบความแม่นยำ: รันชุดข้อมูลทดสอบแล้ววัด Accuracy และดู Confusion Matrix"""

import pandas as pd
import streamlit as st

from nlp_utils import analyze_ticket
from ui import SAMPLE_CSV

st.title("📊 ทดสอบความแม่นยำ")
st.write(
    "รันข้อความในไฟล์ทดสอบผ่านระบบ แล้วเทียบหมวดที่ระบบเลือกกับหมวดที่ถูกต้อง "
    "ไฟล์ต้องมีคอลัมน์ `text` และ `expected_category`"
)

uploaded = st.file_uploader("อัปโหลดไฟล์ CSV (ถ้าไม่อัปโหลดจะใช้ test_tickets.csv)", type="csv")
df = pd.read_csv(uploaded) if uploaded else pd.read_csv(SAMPLE_CSV)

if not {"text", "expected_category"} <= set(df.columns):
    st.error("ไฟล์ต้องมีคอลัมน์ text และ expected_category")
    st.stop()

results = [analyze_ticket(str(t)) for t in df["text"]]
df["predicted"] = [r["category"] for r in results]
df["confidence"] = [r["confidence"] for r in results]
df["priority"] = [r["priority"] for r in results]
df["tokens"] = [", ".join(r["tokens"]) for r in results]
df["correct"] = df["predicted"] == df["expected_category"]

acc = df["correct"].mean()
c1, c2, c3 = st.columns(3)
c1.metric("จำนวนข้อความ", len(df))
c2.metric("Accuracy", f"{acc:.0%}")
c3.metric("ทายผิด", int((~df["correct"]).sum()))

st.markdown("**Confusion Matrix** (แถว = หมวดที่ถูกต้อง, คอลัมน์ = หมวดที่ระบบเลือก)")
cm = pd.crosstab(df["expected_category"], df["predicted"], rownames=["ถูกต้อง"], colnames=["ระบบเลือก"])
st.dataframe(cm, width="stretch")

wrong = df[~df["correct"]]
if len(wrong):
    st.markdown("**ข้อความที่ระบบทายผิด** ใช้ดูว่าควรเพิ่มคีย์เวิร์ดหรือปรับกฎตรงไหน")
    st.dataframe(wrong[["text", "expected_category", "predicted", "tokens"]], hide_index=True, width="stretch")

with st.expander("ผลทั้งหมด"):
    show = df[["text", "expected_category", "predicted", "confidence", "priority", "tokens", "correct"]]
    st.dataframe(show, hide_index=True, width="stretch")
