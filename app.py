import re
import pandas as pd
import streamlit as st
from pythainlp.tokenize import word_tokenize
from pythainlp.corpus import thai_stopwords

st.set_page_config(page_title="Smart IT Ticket Classifier", page_icon="🎫")
st.title("🎫 Smart IT Ticket Classifier")
st.subheader("ระบบวิเคราะห์และคัดแยกหมวดหมู่คำร้อง IT Support อัตโนมัติด้วย NLP")

def clean_text(text):
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)
    text = re.sub(r'\S+@\S+', '', text)
    text = re.sub(r'0\d{8,9}', '', text)
    text = re.sub(r'[^\w\s\u0E00-\u0E7F]', '', text)
    return text.strip()

def process_tokens(text):
    tokens = word_tokenize(text, engine="newmm")
    stops = set(thai_stopwords())
    return [t.strip() for t in tokens if t.strip() and t.strip() not in stops]

def classify_topic(tokens):
    network_kw = ['เน็ต', 'อินเทอร์เน็ต', 'wifi', 'เน็ตช้า', 'เข้าเว็บ', 'เชื่อมต่อ', 'สายแลน']
    hardware_kw = ['เครื่อง', 'ไฟ', 'พิมพ์', 'ปริ้นเตอร์', 'จอ', 'ติด', 'คีย์บอร์ด', 'เมาส์', 'คอม', 'เปิดไม่ติด']
    software_kw = ['รหัส', 'รหัสผ่าน', 'โปรแกรม', 'แอป', 'เข้าไม่ได้', 'ล็อกอิน', 'ลง', 'ติดตั้ง']
    
    score = {'Network': 0, 'Hardware': 0, 'Software': 0}
    for t in tokens:
        t_l = t.lower()
        if t_l in network_kw: score['Network'] += 1
        if t_l in hardware_kw: score['Hardware'] += 1
        if t_l in software_kw: score['Software'] += 1
            
    best = max(score, key=score.get)
    if score[best] == 0: best = "General Support"
    
    mapping = {
        'Network': 'Network Engineer Team',
        'Hardware': 'Hardware Technician Team',
        'Software': 'Software Support Team',
        'General Support': 'Frontline Helpdesk'
    }
    return best, mapping[best]

user_input = st.text_area("📝 พิมพ์อาการเสียหรือปัญหา IT Support:")
if st.button("🚀 ส่งคำร้องและวิเคราะห์ข้อความ"):
    if user_input.strip():
        cleaned = clean_text(user_input)
        tokens = process_tokens(cleaned)
        category, assigned_team = classify_topic(tokens)
        
        st.success(f"✅ ตั๋วของคุณถูกส่งไปยัง: **{assigned_team}**")
        st.info(f"📌 **หมวดหมู่ปัญหา:** {category}")
        st.write("Cleaned Tokens:", tokens)
