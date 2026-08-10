import re
import pandas as pd
import streamlit as st
from pythainlp.tokenize import word_tokenize
from pythainlp.corpus import thai_stopwords
from pythainlp.tag import pos_tag
from pythainlp.tag import NER

# ตั้งค่าหน้าเว็บ Streamlit
st.set_page_config(page_title="Smart IT Ticket Classifier", page_icon="🎫", layout="wide")

st.title("🎫 Smart IT Ticket Classifier")
st.subheader("ระบบวิเคราะห์และคัดแยกหมวดหมู่คำร้อง IT Support อัตโนมัติด้วย NLP")
st.markdown("---")

# ---------------------------------------------------------
# 1. Regex & Cleansing: ลบ Noise (เบอร์โทร, ลิงก์, อีเมล)
# ---------------------------------------------------------
def clean_text(text):
    # ลบ URL/Link
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    # ลบ Email
    text = re.sub(r'\S+@\S+', '', text)
    # ลบ เบอร์โทรศัพท์ (เลข 9-10 หลัก)
    text = re.sub(r'0\d{8,9}', '', text)
    # ลบ อักขระพิเศษ แต่เก็บภาษาไทย อังกฤษ ช่องว่าง
    text = re.sub(r'[^\w\s\u0E00-\u0E7F]', '', text)
    return text.strip()

# ---------------------------------------------------------
# 2. Tokenization & Normalization: ตัดคำ และ ลบ Stopwords
# ---------------------------------------------------------
def process_tokens(text):
    tokens = word_tokenize(text, engine="newmm")
    stops = set(thai_stopwords())
    # กรองช่องว่างและ Stopwords ออก
    cleaned_tokens = [t.strip() for t in tokens if t.strip() and t.strip() not in stops]
    return cleaned_tokens

# ---------------------------------------------------------
# 3. Topic Identification: จำแนกหมวดหมู่ปัญหา IT
# ---------------------------------------------------------
def classify_topic(tokens):
    network_keywords = ['เน็ต', 'อินเทอร์เน็ต', 'wifi', 'เน็ตช้า', 'เข้าเว็บ', 'เชื่อมต่อ', 'สายแลน', 'network', 'เว็บบอร์ด']
    hardware_keywords = ['เครื่อง', 'ไฟ', 'พิมพ์', 'ปริ้นเตอร์', 'จอ', 'ติด', 'คีย์บอร์ด', 'เมาส์', 'คอม', 'hardware', 'เปิดไม่ติด']
    software_keywords = ['รหัส', 'รหัสผ่าน', 'โปรแกรม', 'แอป', 'เข้าไม่ได้', 'ล็อกอิน', 'software', 'ลง', 'ติดตั้ง', 'พาสเวิร์ด']
    
    score = {'Network': 0, 'Hardware': 0, 'Software': 0}
    
    for t in tokens:
        t_lower = t.lower()
        if t_lower in network_keywords:
            score['Network'] += 1
        if t_lower in hardware_keywords:
            score['Hardware'] += 1
        if t_lower in software_keywords:
            score['Software'] += 1
            
    # เลือกหมวดหมู่ที่ได้คะแนนสูงสุด
    best_category = max(score, key=score.get)
    if score[best_category] == 0:
        best_category = "General Support" # หมวดทั่วไปกรณีไม่ตรงคีย์เวิร์ด
        
    mapping_team = {
        'Network': 'Network Engineer Team',
        'Hardware': 'Hardware Technician Team',
        'Software': 'Software Support Team',
        'General Support': 'Frontline Helpdesk'
    }
    return best_category, mapping_team[best_category]

# ---------------------------------------------------------
# 4. POS & NER: ดึงคำสำคัญและสกัดชื่อเฉพาะ
# ---------------------------------------------------------
def extract_pos_ner(tokens):
    pos_tags = pos_tag(tokens, engine="perceptron")
    try:
        ner_engine = NER(engine="thaimodel")
        ner_tags = ner_engine.tag(" ".join(tokens))
    except:
        ner_tags = []
    return pos_tags, ner_tags

# =========================================================
# ส่วนของหน้าจอ UI (User Interface)
# =========================================================
user_input = st.text_area("📝 พิมพ์อาการเสียหรือปัญหา IT Support ที่ต้องการแจ้งซ่อม:", 
                          placeholder="เช่น เข้าเว็บไม่ได้ เน็ตช้ามาก ติดต่อ คุณสมชาย เบอร์ 0812345678", 
                          height=100)

if st.button("🚀 ส่งคำร้องและวิเคราะห์ข้อความ"):
    if user_input.strip() == "":
        st.warning("กรุณากรอกข้อความก่อนกดวิเคราะห์")
    else:
        # Step 1: Cleansing
        cleaned = clean_text(user_input)
        
        # Step 2: Tokenization
        tokens = process_tokens(cleaned)
        
        # Step 3: Topic Classification
        category, assigned_team = classify_topic(tokens)
        
        # Step 4: POS & NER
        pos_tags, ner_tags = extract_pos_ner(tokens)
        
        # --- แสดงผลการคัดแยกหมวดหมู่ (Output หลัก) ---
        st.success(f"✅ ตั๋วของคุณถูกส่งไปยัง: **{assigned_team}** เรียบร้อยแล้ว")
        st.info(f"📌 **หมวดหมู่ปัญหา:** {category}")
        
        st.markdown("---")
        st.subheader("🔍 เบื้องหลังการประมวลผลทาง NLP (NLP Pipeline Analysis)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 1. Regex & Cleansing")
            st.text(f"ข้อความหลังลบ Noise (เบอร์/ลิงก์):\n{cleaned}")
            
            st.markdown("### 2. Tokenization & Stopwords Removal")
            st.write("คำที่สกัดได้ (Cleaned Tokens):", tokens)
            
        with col2:
            st.markdown("### 3. POS Tagging (ระบุหน้าที่ของคำ)")
            df_pos = pd.DataFrame(pos_tags, columns=['คำศัพท์ (Word)', 'หน้าที่ (POS Tag)'])
            st.dataframe(df_pos, use_container_width=True)
            
            if ner_tags:
                st.markdown("### 4. Named Entity Recognition (NER)")
                st.write(ner_tags)