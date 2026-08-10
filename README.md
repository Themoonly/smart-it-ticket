# 🎫 Smart Ticket: ระบบวิเคราะห์และคัดแยกหมวดหมู่คำร้อง IT Support อัตโนมัติ

Web Application สำหรับวิเคราะห์อาการเสีย คัดกรอง และส่งต่อตั๋วแจ้งซ่อม IT Support ภาษาไทย/อังกฤษ ไปยังทีมช่างเทคนิคที่เกี่ยวข้องแบบอัตโนมัติ ช่วยลดปัญหาคอขวด (Bottleneck) และเพิ่มความเร็วในการให้บริการภายในองค์กร

---

## 🎯 แนวคิดของ Domain (Domain Concept)

ในองค์กรขนาดใหญ่ เมื่อผู้ใช้งานแจ้งปัญหาไอทีเข้ามา เจ้าหน้าที่ IT Support ด่านหน้า (Frontline Helpdesk) ต้องเสียเวลานั่งอ่านข้อความทีละฉบับเพื่อจำแนกประเภทงาน ส่งผลให้เกิดความล่าช้า 

โครงการ **Smart Ticket** นำเทคโนโลยี **Natural Language Processing (NLP)** เข้ามาประมวลผลข้อความภาษาไทย/อังกฤษ เพื่อวิเคราะห์เจตนาของผู้ใช้ (Intent Analysis) และจัดหมวดหมู่คำร้องให้อัตโนมัติทันทีที่กดส่งคำร้อง

### การจัดกลุ่มหมวดหมู่หลัก (Categories):
1. **Network:** ปัญหาอินเทอร์เน็ต, Wi-Fi, เว็บไซต์, ระบบเครือข่าย $\rightarrow$ *ส่งต่อไปยัง Network Engineer Team*
2. **Hardware:** ปัญหาอุปกรณ์กายภาพ, ปริ้นเตอร์, ปลั๊กไฟ, จอภาพ, เครื่องเปิดไม่ติด $\rightarrow$ *ส่งต่อไปยัง Hardware Technician Team*
3. **Software:** ปัญหาโปรแกรม, ระบบปฏิบัติการ, ลืมรหัสผ่าน, เข้าใช้งานแอปไม่ได้ $\rightarrow$ *ส่งต่อไปยัง Software Support Team*

---

## 🛠️ เทคนิคทาง NLP ที่นำมาประยุกต์ใช้ (NLP Techniques)

1. **Regex & Cleansing:** ลบข้อมูลรบกวน (Noise) และข้อมูลส่วนตัวออก เช่น เบอร์โทรศัพท์, ลิงก์ URL, อีเมล และอักขระพิเศษ
2. **Tokenization & Normalization:** ตัดคำภาษาไทยด้วย PyThaiNLP (`newmm`) และกรองคำหยุดยั้ง (Stopwords) ออกเพื่อเหลือไว้เฉพาะคำสำคัญ
3. **Topic Identification:** จำแนกประเภทงานแจ้งซ่อมแบบ Rule-based Keyword Matching และจัดหมวดหมู่พร้อมระบุทีมรับผิดชอบ
4. **POS & NER Tagging:** ระบุหน้าที่ของคำ (Part-of-Speech Tagging) เพื่อช่วยให้ระบบเข้าใจโครงสร้างประโยค

---

## 🤖 ตัวอย่าง Prompt AI ที่ใช้ในการพัฒนาระบบ

> "ช่วยพัฒนาระบบ Web Application บน Streamlit สำหรับวิเคราะห์และคัดแยกหมวดหมู่ตั๋วแจ้งซ่อม IT Support ภาษาไทย โดยใช้เทคโนโลยี NLP จากไลบรารี PyThaiNLP ทำการ Cleansing ลบเบอร์โทรและลิงก์ด้วย Regex, ทำ Tokenization กรอง Stopwords ออก, คัดแยกหมวดหมู่เป็น Network/Hardware/Software และแสดงผล POS Tagging ผ่านหน้าจอแบบ Interactive"

---

## 📂 โครงสร้างโฟลเดอร์ของโครงการ (Repository Structure)

```text
smart-it-ticket/
├── app.py                # โค้ดหลักของแอป Streamlit และระบบ NLP Pipeline
├── requirements.txt      # รายชื่อไลบรารีที่จำเป็นสำหรับการ Deploy
├── test_tickets.csv     # ชุดข้อมูลจำลองสำหรับใช้ทดสอบระบบ
└── README.md             # เอกสารอธิบายรายละเอียดโครงการ
