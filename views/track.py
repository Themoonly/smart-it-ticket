"""หน้าติดตามตั๋ว: ผู้แจ้งกรอกเลขตั๋วเพื่อดูว่าส่งไปทีมไหนและสถานะล่าสุด"""

import streamlit as st

import db
from nlp_utils import ALL_TEAMS, FALLBACK_TEAM, TEAM_TO_CATEGORY
from ui import entities_text, priority_badge, status_badge, status_progress

SNIPPET_LEN = 40
STATUS_OPEN, STATUS_DONE, STATUS_ALL = "ยังไม่เสร็จ", "เสร็จแล้ว", "ทั้งหมด"
TAB_ALL_LABEL = "ทั้งหมด"

# ไอคอนต่อ "หมวด" (ไม่ใช่ชื่อทีม) แล้วค่อยจับคู่กับทีมจาก ALL_TEAMS/TEAM_TO_CATEGORY
# เพื่อไม่ต้องเขียนชื่อทีมซ้ำจาก nlp_utils.py
_CATEGORY_ICON = {"Network": "🌐", "Hardware": "🖥️", "Software": "💻"}
HELPDESK_ICON = "🙋"

TEAM_ICON = {
    team: (HELPDESK_ICON if team == FALLBACK_TEAM else _CATEGORY_ICON.get(TEAM_TO_CATEGORY[team], HELPDESK_ICON))
    for team in ALL_TEAMS
}
TEAM_SHORT = {
    team: ("Helpdesk" if team == FALLBACK_TEAM else TEAM_TO_CATEGORY[team])
    for team in ALL_TEAMS
}


def _snippet(text: str) -> str:
    text = text.strip()
    return text if len(text) <= SNIPPET_LEN else text[:SNIPPET_LEN].rstrip() + "…"


def _show_ticket(ticket_id: str) -> None:
    st.session_state.track_input = ticket_id


def _matches_status(ticket: dict, status_filter: str) -> bool:
    if status_filter == STATUS_OPEN:
        return ticket["status"] != "เสร็จสิ้น"
    if status_filter == STATUS_DONE:
        return ticket["status"] == "เสร็จสิ้น"
    return True


def _ticket_card(t: dict, tab_key: str) -> None:
    with st.container(border=True):
        left, right = st.columns([5, 2])
        left.markdown(f"{priority_badge(t['priority'])} · **{t['ticket_id']}**")
        left.write(_snippet(t["raw_text"]))
        left.caption(f"{t['subcategory']} · {status_badge(t['status'])} · แจ้งเมื่อ {t['created_at']}")
        right.button(
            "ดูรายละเอียด", key=f"view_{tab_key}_{t['id']}", width="stretch",
            on_click=_show_ticket, args=(t["ticket_id"],),
        )


st.title("🔎 ติดตามตั๋ว")
st.write("กรอกเลขตั๋วเพื่อดูว่าคำร้องของคุณถูกส่งไปทีมไหน และตอนนี้อยู่ในขั้นตอนใด")

my_ticket_ids = st.session_state.get("my_tickets", [])

if not my_ticket_ids:
    st.info("ยังไม่มีตั๋วที่คุณส่งในรอบนี้")
    st.page_link("views/submit.py", label="ไปหน้าแจ้งปัญหาเพื่อส่งตั๋วใหม่", icon="📝")
else:
    st.subheader("ตั๋วของฉัน")

    ids = [n for n in (db.parse_ticket_id(tid) for tid in my_ticket_ids) if n is not None]
    my_tickets = db.get_tickets(ids)

    status_filter = st.radio("สถานะ", [STATUS_OPEN, STATUS_DONE, STATUS_ALL], horizontal=True)
    filtered = [t for t in my_tickets if _matches_status(t, status_filter)]

    tab_defs = [("all", None)] + [(team, team) for team in ALL_TEAMS]
    tab_labels = [f"{TAB_ALL_LABEL} ({len(filtered)})"] + [
        f"{TEAM_ICON[team]} {TEAM_SHORT[team]} ({sum(1 for t in filtered if t['team'] == team)})"
        for team in ALL_TEAMS
    ]

    tabs = st.tabs(tab_labels)
    for tab, (tab_key, team_filter) in zip(tabs, tab_defs):
        with tab:
            subset = filtered if team_filter is None else [t for t in filtered if t["team"] == team_filter]
            if not subset:
                if team_filter is None:
                    st.info(f"ไม่มีตั๋วที่ตรงกับตัวกรอง \"{status_filter}\"")
                else:
                    st.info(f"ยังไม่มีตั๋วที่ส่งไป {team_filter}")
            else:
                for t in subset:
                    _ticket_card(t, tab_key)

st.divider()

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

    st.caption("สถานะตั๋วเปลี่ยนได้โดยผู้ดูแลเท่านั้น")

    c1, c2, c3 = st.columns(3)
    # ใช้ markdown แทน st.metric เพราะชื่อทีมยาว metric จะตัดเป็น "Hardware Techni…"
    c1.caption("ทีมที่ดูแล")
    c1.markdown(f"**{ticket['team']}**")
    c2.caption("หมวดหมู่")
    c2.markdown(f"**{ticket['category']}** · {ticket['subcategory']}")
    c3.caption("ความเร่งด่วน")
    c3.markdown(f"**{priority_badge(ticket['priority'])}**")

    if ticket["reassigned"]:
        st.info(f"ตั๋วนี้ถูกย้ายจาก {ticket['original_team']} มายัง {ticket['team']} โดยเจ้าหน้าที่")
    elif ticket["needs_review"]:
        st.warning("ตั๋วนี้รอเจ้าหน้าที่ตรวจสอบก่อนส่งต่อ เพราะระบบยังไม่มั่นใจในหมวดหมู่")

    if ticket["note"]:
        st.markdown(f"**ข้อความจากทีมดูแล:** {ticket['note']}")

    st.markdown(entities_text(ticket["entities"]))
    st.caption(f"แจ้งเมื่อ {ticket['created_at']} · อัปเดตล่าสุด {ticket['updated_at']}")
