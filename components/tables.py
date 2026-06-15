"""List-view (table) rendering for IP3 results."""
from __future__ import annotations

import streamlit as st

from components import badges, cards, layout
from utils import db, text_utils

_COLS = [0.5, 0.4, 3.4, 0.7, 1.6, 1.1, 1.0, 0.8, 0.8, 0.8]
_HEADERS = ["선택", "순위", "특허명", "국가", "출원인", "출원일", "유사도", "도면", "청구항", "상세"]


def render_table(case_id: int, patents: list[dict], ctx: str = "결과") -> None:
    header = st.columns(_COLS)
    for col, label in zip(header, _HEADERS):
        col.markdown(f"<div class='ip3-section'>{label}</div>", unsafe_allow_html=True)
    st.markdown("<hr/>", unsafe_allow_html=True)

    for patent in patents:
        pid = patent["id"]
        selected = pid in st.session_state.selected_patent_ids
        row = st.columns(_COLS)
        if row[0].button(
            "✅" if selected else "⬜", key=f"lsel_{ctx}_{pid}", use_container_width=True
        ):
            layout.toggle_select(pid)
            st.rerun()
        row[1].write(patent.get("rank", ""))
        title = text_utils.truncate(patent.get("title", ""), 60)
        status = ""
        if patent.get("is_interested") and patent.get("interest_status"):
            status = f" {badges.interest(patent['interest_status'])}"
        if patent.get("is_excluded"):
            status += f" {badges.status_pill('제외')}"
        row[2].markdown(
            f"<span class='ip3-meta' style='font-weight:600;color:#1F2933'>{title}</span>{status}",
            unsafe_allow_html=True,
        )
        row[3].markdown(badges.country(patent.get("country", "")), unsafe_allow_html=True)
        row[4].markdown(
            f"<span class='ip3-meta'>{text_utils.truncate(patent.get('applicant',''),18)}</span>",
            unsafe_allow_html=True,
        )
        row[5].markdown(
            f"<span class='ip3-meta'>{patent.get('filing_date','') or '-'}</span>",
            unsafe_allow_html=True,
        )
        row[6].markdown(
            badges.similarity(patent.get("similarity_score", 0)), unsafe_allow_html=True
        )
        if row[7].button("🖼", key=f"ldr_{ctx}_{pid}", help="도면", use_container_width=True):
            layout.open_detail(pid, "도면")
            st.rerun()
        if row[8].button("§", key=f"lc_{ctx}_{pid}", help="청구항", use_container_width=True):
            layout.open_detail(pid, "청구항")
            st.rerun()
        if row[9].button("🔍", key=f"ld_{ctx}_{pid}", help="상세", use_container_width=True):
            layout.open_detail(pid, "요약")
            st.rerun()
