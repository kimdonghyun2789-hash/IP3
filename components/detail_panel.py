"""Right-hand slide-in detail panel (요약 / 도면 / 청구항 / 서지정보)."""
from __future__ import annotations

import streamlit as st

from components import badges, cards, layout
from services import cache_service
from utils import db


def render() -> None:
    """Render the detail panel for the currently opened patent."""
    pid = st.session_state.get("detail_patent_id")
    if not pid:
        return
    patent = db.get_patent(pid)
    if not patent:
        layout.close_detail()
        return

    case_id = st.session_state.get("current_case_id")
    cp = db.get_case_patent(case_id, pid) if case_id else None
    details = cache_service.ensure_details(pid)

    with st.container(border=True):
        st.markdown("<div class='ip3-panel'></div>", unsafe_allow_html=True)
        head = st.columns([6, 1])
        head[0].markdown(
            f"<div class='ip3-patent-title'>{patent.get('title','')}</div>",
            unsafe_allow_html=True,
        )
        if head[1].button("✕", key="close_detail", help="패널 닫기"):
            layout.close_detail()
            st.rerun()

        st.markdown(
            badges.country(patent.get("country", ""))
            + " &nbsp; "
            + badges.similarity(cp.get("similarity_score", 0) if cp else 0),
            unsafe_allow_html=True,
        )

        tab = st.radio(
            "패널탭",
            ["요약", "도면", "청구항", "서지정보"],
            horizontal=True,
            label_visibility="collapsed",
            index=["요약", "도면", "청구항", "서지정보"].index(
                st.session_state.get("detail_tab", "요약")
            ),
            key="detail_panel_tab",
        )
        st.session_state.detail_tab = tab
        st.markdown("<hr/>", unsafe_allow_html=True)

        if tab == "요약":
            st.write(patent.get("abstract", "") or "요약 정보 없음")
        elif tab == "도면":
            urls = details.get("drawing_urls", [])
            if urls:
                layout.thumbnails(urls, max_show=12)
                st.caption(f"도면 {len(urls)}건 (URL/메타정보 기준)")
            else:
                st.caption("도면 정보 없음")
        elif tab == "청구항":
            claims = details.get("claims_text", "")
            st.write(claims if claims else "청구항 정보 없음")
        elif tab == "서지정보":
            _bibliography(patent)

        st.markdown("<hr/>", unsafe_allow_html=True)
        actions = st.columns(3)
        if cp:
            star_label = "⭐ 관심 해제" if cp.get("is_interested") else "☆ 관심특허 등록"
            if actions[0].button(star_label, key="panel_star", use_container_width=True):
                cards._toggle_interest(cp["link_id"], cp)
                st.rerun()
            sel = pid in st.session_state.selected_patent_ids
            sel_label = "✅ 비교대상 해제" if sel else "☐ 비교대상 추가"
            if actions[1].button(sel_label, key="panel_sel", use_container_width=True):
                layout.toggle_select(pid)
                st.rerun()
        if actions[2].button("전체 보기", key="panel_full", use_container_width=True):
            layout.goto(
                "patent_detail", detail_patent_id=pid, detail_return="review_result"
            )


def _bibliography(patent: dict) -> None:
    fields = [
        ("출원번호", patent.get("application_no")),
        ("공개번호", patent.get("publication_no")),
        ("등록번호", patent.get("registration_no")),
        ("출원인", patent.get("applicant")),
        ("발명자", patent.get("inventor")),
        ("출원일", patent.get("filing_date")),
        ("공개일", patent.get("publication_date")),
        ("등록일", patent.get("registration_date")),
        ("IPC", patent.get("ipc")),
        ("CPC", patent.get("cpc")),
        ("법적상태", patent.get("legal_status")),
    ]
    html = "".join(
        f"<div class='ip3-kv'><b>{k}</b> &nbsp;{v or '-'}</div>" for k, v in fields
    )
    st.markdown(html, unsafe_allow_html=True)
    if patent.get("source_url"):
        st.markdown(f"[원문 링크 ↗]({patent['source_url']})")
