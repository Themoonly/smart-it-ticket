# smart-it-ticket
Smart Ticket: ระบบวิเคราะห์และคัดแยกหมวดหมู่คำร้อง IT Support อัตโนมัติ

# 🎫 Smart Ticket: ระบบวิเคราะห์และคัดแยกหมวดหมู่คำร้อง IT Support อัตโนมัติ

Web Application สำหรับวิเคราะห์อาการเสียและคัดแยกหมวดหมู่ตั๋วแจ้งซ่อม IT อัตโนมัติด้วยเทคโนโลยี Natural Language Processing (NLP)

## 🛠️ คุณสมบัติทางเทคนิค (NLP Techniques)
1. **Regex & Cleansing:** ลบเบอร์โทรศัพท์, ลิงก์ URL, อีเมล และอักขระขยะออกจากข้อความแจ้งซ่อม
2. **Tokenization & Normalization:** ตัดคำภาษาไทยด้วย PyThaiNLP (`newmm`) พร้อมกรอง Stop words
3. **Topic Identification:** วิเคราะห์เจตนาและจัดกลุ่มหัวข้อปัญหา (Network, Hardware, Software)
4. **POS & NER Tagging:** ระบุหน้าที่ของคำและสกัดชื่อบุคคล/สถานที่/เวลา

## 🤖 ตัวอย่าง Prompt AI ที่ใช้สั่งพัฒนาระบบ
> "ช่วยสร้าง Web Application บน Streamlit สำหรับคัดแยกหมวดหมู่ตั๋วแจ้งซ่อม IT Support ภาษาไทย โดยใช้ไลบรารี PyThaiNLP ทำ Regex ลบเบอร์โทรศัพท์, ทำ Tokenization ตัดคำและลบ Stop words, จำแนกหัวข้อ Network/Hardware/Software และแสดงผล POS Tagging บนหน้าจอ"

## 🚀 วิธีการติดตั้งและรันบนเครื่อง Local
```bash
pip install -r requirements.txt
streamlit run app.py