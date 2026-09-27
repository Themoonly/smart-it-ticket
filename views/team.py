"""หน้าทีมดูแล: ช่างแต่ละทีมเห็นเฉพาะตั๋วของทีมตัวเอง อัปเดตสถานะ และแจ้งส่งผิดทีมได้"""

from datetime import datetime

import pandas as pd
import streamlit as st

import auth
import db
from nlp_utils import ALL_TEAMS, TEAM_TO_CATEGORY
from ui import entities_text, load_sample_tickets, priority_badge, status_badge

OVERVIEW = "📈 ภาพรวมทุกทีม"
REVIEW = "👀 คิว Human Review"
SLA_HIGH_MINUTES = 30  # ตั๋ว High ที่ยัง "รอรับเรื่อง" เกินเวลานี้จะขึ้นคำเตือนบนการ์ด

auth.require_admin()  # ไม่ใช่ admin จะเห็นฟอร์มล็อกอินและหยุดตรงนี้

st.title("🛠️ หน้าทีมดูแล")

with st.sidebar:
    st.markdown("**ข้อมูลเดโม**")
    if st.button("โหลดตั๋วตัวอย่าง", width="stretch"):
        n = load_sample_tickets()
        st.toast(f"เพิ่มตั๋วตัวอย่าง {n} ใบแล้ว")
    if st.button("ล้างตั๋วทั้งหมด", width="stretch"):
        db.clear_all()
        st.toast("ล้างตั๋วทั้งหมดแล้ว")

new_counts = db.get_new_counts()


def _view_label(v: str) -> str:
    if v not in ALL_TEAMS:
        return v
    return f"{v} (ใหม่ {new_counts.get(v, 0)})"


view = st.selectbox("เลือกมุมมอง", [OVERVIEW, REVIEW] + ALL_TEAMS, format_func=_view_label)


def ticket_card(t: dict, key_prefix: str, review_mode: bool = False) -> None:
    title = f"{priority_badge(t['priority'])} · {t['ticket_id']} · {status_badge(t['status'])}"
    with st.expander(title, expanded=t["status"] != "เสร็จสิ้น" and t["priority"] == "High"):
        if t["priority"] == "High" and t["status"] == db.STATUSES[0]:
            created = datetime.strptime(t["created_at"], "%Y-%m-%d %H:%M").replace(tzinfo=db.TZ)
            waited = int((datetime.now(db.TZ) - created).total_seconds() // 60)
            if waited > SLA_HIGH_MINUTES:
                st.error(f"⚠️ รอเกิน {SLA_HIGH_MINUTES} นาที (รอมา {waited} นาที)")

        st.markdown(f"> {t['raw_text']}")
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**หมวด:** {t['category']}  \n**หมวดย่อย:** {t['subcategory']}")
        c2.markdown(f"**ความมั่นใจ:** {int(t['confidence'] * 100)}%  \n**แจ้งเมื่อ:** {t['created_at']}")
        c3.markdown(entities_text(t["entities"]))

        if t["reassigned"]:
            st.caption(f"ย้ายมาจาก {t['original_team']}")
        if t["needs_review"]:
            st.warning(f"รอตรวจสอบ: {t['review_reason']}")

        k = f"{key_prefix}_{t['id']}"

        if review_mode:
            st.markdown(f"ระบบเลือก **{t['team']}**")
            r1, r2, r3 = st.columns([1, 2, 1])
            if r1.button("ยืนยันทีมนี้", key=f"ok_{k}", disabled=t["team"] == "Frontline Helpdesk"):
                db.confirm_team(t["id"])
                st.rerun()
            target = r2.selectbox("ส่งไปทีม", ALL_TEAMS, key=f"tg_{k}", label_visibility="collapsed")
            if r3.button("ส่งต่อ", key=f"mv_{k}", type="primary"):
                db.reassign_ticket(t["id"], target, TEAM_TO_CATEGORY[target])
                st.rerun()
            return

        s1, s2 = st.columns([1, 2])
        status = s1.selectbox("สถานะ", db.STATUSES, index=db.STATUSES.index(t["status"]), key=f"st_{k}")
        note = s2.text_input("ข้อความถึงผู้แจ้ง", value=t["note"], key=f"nt_{k}")
        if st.button("บันทึก", key=f"sv_{k}", type="primary"):
            db.update_status(t["id"], status, note)
            st.toast(f"บันทึก {t['ticket_id']} แล้ว")
            st.rerun()

        with st.popover("ส่งผิดทีม?"):
            others = [x for x in ALL_TEAMS if x != t["team"]]
            target = st.selectbox("ย้ายไปทีม", others, key=f"rt_{k}")
            if st.button("ย้ายตั๋ว", key=f"rb_{k}"):
                db.reassign_ticket(t["id"], target, TEAM_TO_CATEGORY[target])
                st.rerun()


if view == OVERVIEW:
    s = db.get_stats()
    if s["total"] == 0:
        st.info("ยังไม่มีตั๋วในระบบ แจ้งปัญหาที่หน้า \"แจ้งปัญหา\" หรือกด \"โหลดตั๋วตัวอย่าง\" ที่แถบด้านซ้าย")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ตั๋วทั้งหมด", s["total"])
    c2.metric("คัดแยกอัตโนมัติ", f"{s['auto_routed'] / s['total']:.0%}")
    c3.metric("รอ Human Review", s["pending_review"])
    acc = s["routing_accuracy"]
    c4.metric(
        "ส่งถูกทีม", f"{acc:.0%}" if acc is not None else "-",
        help="คิดจากตั๋วที่ระบบส่งอัตโนมัติ ลบด้วยตั๋วที่ช่างกด \"ส่งผิดทีม\"",
    )

    st.markdown("**ตั๋วใหม่ (รอรับเรื่อง) ต่อทีม**")
    # ใช้ markdown แทน st.metric เพราะชื่อทีมยาว metric จะตัดเป็น "Hardware Techni…"
    team_cols = st.columns(len(ALL_TEAMS))
    for col, team in zip(team_cols, ALL_TEAMS):
        col.markdown(f"**{team}**  \nใหม่ {new_counts.get(team, 0)}")

    left, right = st.columns(2)
    left.markdown("**จำนวนตั๋วแยกตามทีม**")
    left.bar_chart(pd.Series(s["by_team"], name="ตั๋ว"), horizontal=True, height=220)
    right.markdown("**จำนวนตั๋วแยกตามสถานะ**")
    right.bar_chart(pd.Series(s["by_status"], name="ตั๋ว"), horizontal=True, height=220)

    st.markdown("**ตั๋วทั้งหมด**")
    rows = db.list_tickets()
    df = pd.DataFrame(rows)[["ticket_id", "raw_text", "team", "category", "priority", "status", "created_at"]]
    df.columns = ["เลขตั๋ว", "ข้อความ", "ทีม", "หมวด", "ความเร่งด่วน", "สถานะ", "แจ้งเมื่อ"]
    st.dataframe(df, hide_index=True, width="stretch")

elif view == REVIEW:
    st.write("ตั๋วที่ระบบไม่มั่นใจ ให้เจ้าหน้าที่ยืนยันหรือเลือกทีมที่ถูกต้อง")
    tickets = db.list_tickets(review_only=True)
    if not tickets:
        st.success("ไม่มีตั๋วรอตรวจสอบ")
    for t in tickets:
        ticket_card(t, "rv", review_mode=True)

else:
    tickets = db.list_tickets(team=view)
    open_count = sum(t["status"] != "เสร็จสิ้น" for t in tickets)
    high_count = sum(t["priority"] == "High" and t["status"] != "เสร็จสิ้น" for t in tickets)
    c1, c2, c3 = st.columns(3)
    c1.metric("ตั๋วของทีม", len(tickets))
    c2.metric("ยังไม่เสร็จ", open_count)
    c3.metric("ด่วน (ยังไม่เสร็จ)", high_count)

    if not tickets:
        st.info(f"ยังไม่มีตั๋วที่ส่งมายัง {view}")
    for t in tickets:
        ticket_card(t, "tm")
