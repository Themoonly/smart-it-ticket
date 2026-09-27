"""
auth.py — ระบบล็อกอินผู้ดูแล (admin)
เฉพาะ admin เท่านั้นที่เปลี่ยนสถานะตั๋ว ย้ายทีม และจัดการข้อมูลเดโมได้

รหัสผ่านเก็บใน Streamlit Secrets ไม่เก็บในโค้ด:
  - รันในเครื่อง: สร้างไฟล์ .streamlit/secrets.toml แล้วใส่  ADMIN_PASSWORD = "รหัสผ่าน"
  - Streamlit Cloud: Manage app > Settings > Secrets แล้วใส่บรรทัดเดียวกัน
"""

import hmac
import time

import streamlit as st

MAX_ATTEMPTS = 5      # ใส่รหัสผิดได้กี่ครั้งก่อนถูกล็อก
LOCK_SECONDS = 60     # ล็อกนานกี่วินาที


def _admin_password() -> str | None:
    try:
        return st.secrets.get("ADMIN_PASSWORD")
    except FileNotFoundError:  # ยังไม่มีไฟล์ secrets เลย
        return None


def is_admin() -> bool:
    return st.session_state.get("is_admin", False)


def logout() -> None:
    st.session_state.is_admin = False


def _login_form(password: str) -> None:
    state = st.session_state
    locked_until = state.get("login_locked_until", 0)
    remaining = int(locked_until - time.time())
    if remaining > 0:
        st.error(f"ใส่รหัสผ่านผิดหลายครั้ง ลองใหม่ได้ใน {remaining} วินาที")
        return

    with st.form("admin_login"):
        entered = st.text_input("รหัสผ่านผู้ดูแล", type="password")
        submitted = st.form_submit_button("เข้าสู่ระบบ", type="primary")

    if not submitted:
        return

    # compare_digest ป้องกันการเดารหัสจากเวลาที่ใช้เปรียบเทียบ
    if hmac.compare_digest(entered.encode(), password.encode()):
        state.is_admin = True
        state.login_attempts = 0
        st.rerun()

    state.login_attempts = state.get("login_attempts", 0) + 1
    left = MAX_ATTEMPTS - state.login_attempts
    if left <= 0:
        state.login_locked_until = time.time() + LOCK_SECONDS
        state.login_attempts = 0
        st.error(f"ใส่รหัสผ่านผิด {MAX_ATTEMPTS} ครั้ง ระบบล็อกไว้ {LOCK_SECONDS} วินาที")
    else:
        st.error(f"รหัสผ่านไม่ถูกต้อง เหลืออีก {left} ครั้ง")


def require_admin() -> None:
    """เรียกบรรทัดแรกของหน้าที่ต้องเป็น admin ถ้ายังไม่ล็อกอินจะแสดงฟอร์มแล้วหยุดการทำงานของหน้า"""
    if is_admin():
        return

    st.title("🔐 สำหรับผู้ดูแลเท่านั้น")
    st.write("หน้านี้ใช้เปลี่ยนสถานะตั๋วและย้ายทีม กรุณาเข้าสู่ระบบด้วยรหัสผ่านผู้ดูแล")

    password = _admin_password()
    if not password:
        st.error(
            "ยังไม่ได้ตั้งรหัสผ่านผู้ดูแล  \n"
            "ในเครื่อง: สร้างไฟล์ `.streamlit/secrets.toml` แล้วใส่ `ADMIN_PASSWORD = \"รหัสผ่าน\"`  \n"
            "บน Streamlit Cloud: Manage app → Settings → Secrets แล้วใส่บรรทัดเดียวกัน"
        )
        st.stop()

    _login_form(password)
    st.caption("ผู้แจ้งปัญหาติดตามสถานะตั๋วได้ที่หน้า \"ติดตามตั๋ว\" โดยไม่ต้องเข้าสู่ระบบ")
    st.stop()
