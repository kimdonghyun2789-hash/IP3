"""Result / patent card rendering for IP3."""
from __future__ import annotations

import streamlit as st

from components import badges, layout
from utils import db

DEFAULT_INTEREST = "참고"


def _meta_line(patent: dict) -> str:
    bits = [
        badges.country(patent.get("country", "")),
        f"<span class='ip3-meta'>{patent.get('applicant', '') or '출원인 미상'}</span>",
        f"<span class='ip3-meta'>출원일 {patent.get('filing_date', '') or '-'}</span>",
    ]
    return " &nbsp;·&nbsp; ".join(bits)


def render_card(case_id: int, patent: dict, ctx: str = "결과") -> None:
    """Render one patent as a card. ``patent`` is a joined case_patent row."""
    pid = patent["id"]
    link_id = patent.get("link_id")
    selected = pid in st.session_state.selected_patent_ids

    with st.container(border=True):
        left, body, right = st.columns([0.85, 6.0, 1.25])

        with left:
            if st.button(
                "✅" if selected else "⬜",
                key=f"sel_{ctx}_{pid}",
                help="비교대상 선택",
                use_container_width=True,
            ):
                layout.toggle_select(pid)
                st.rerun()
            if st.button(
                "⭐" if patent.get("is_interested") else "☆",
                key=f"star_{ctx}_{pid}",
                help="관심특허 등록",
                use_container_width=True,
            ):
                _toggle_interest(link_id, patent)
                st.rerun()
            if st.button(
                "🚫" if patent.get("is_excluded") else "⊘",
                key=f"exc_{ctx}_{pid}",
                help="제외",
                use_container_width=True,
            ):
                _toggle_exclude(link_id, patent, pid)
                st.rerun()

        with body:
            rank = patent.get("rank", "")
            st.markdown(
                f"<div class='ip3-patent-title'>{rank}. {patent.get('title', '')}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(_meta_line(patent), unsafe_allow_html=True)
            status_chips = []
            if patent.get("is_interested") and patent.get("interest_status"):
                status_chips.append(badges.interest(patent["interest_status"]))
            if patent.get("is_excluded"):
                status_chips.append(badges.status_pill("제외됨"))
            if status_chips:
                st.markdown(" ".join(status_chips), unsafe_allow_html=True)

            details = db.get_patent_details(pid) or {}
            drawing_urls = (details.get("drawing_meta", {}) or {}).get("drawing_urls", [])
            layout.thumbnails(drawing_urls)

        with right:
            st.markdown(
                badges.similarity(patent.get("similarity_score", 0)),
                unsafe_allow_html=True,
            )

        # Action row kept at card level (avoids 3-deep column nesting).
        a1, a2, a3, a4 = st.columns(4)
        if a1.button("상세", key=f"d_{ctx}_{pid}", use_container_width=True):
            layout.open_detail(pid, "요약")
            st.rerun()
        if a2.button("도면", key=f"dr_{ctx}_{pid}", use_container_width=True):
            layout.open_detail(pid, "도면")
            st.rerun()
        if a3.button("청구항", key=f"c_{ctx}_{pid}", use_container_width=True):
            layout.open_detail(pid, "청구항")
            st.rerun()
        if a4.button("전체 보기", key=f"full_{ctx}_{pid}", use_container_width=True):
            layout.goto(
                "patent_detail",
                detail_patent_id=pid,
                detail_return="review_result",
            )

        with st.expander("펼치기"):
            _render_expanded(patent)


def _render_expanded(patent: dict) -> None:
    pid = patent["id"]
    details = db.get_patent_details(pid) or {}
    drawing_urls = (details.get("drawing_meta", {}) or {}).get("drawing_urls", [])

    layout.section_label("대표도면")
    if drawing_urls:
        layout.thumbnails(drawing_urls, max_show=8)
    else:
        st.caption("도면 정보 없음")

    layout.section_label("요약")
    st.write(patent.get("abstract", "") or "요약 정보 없음")

    cols = st.columns(2)
    with cols[0]:
        st.markdown(
            f"<div class='ip3-kv'><b>출원번호</b> {patent.get('application_no', '') or '-'}</div>"
            f"<div class='ip3-kv'><b>공개번호</b> {patent.get('publication_no', '') or '-'}</div>"
            f"<div class='ip3-kv'><b>등록번호</b> {patent.get('registration_no', '') or '-'}</div>",
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            f"<div class='ip3-kv'><b>IPC</b> {patent.get('ipc', '') or '-'}</div>"
            f"<div class='ip3-kv'><b>CPC</b> {patent.get('cpc', '') or '-'}</div>"
            f"<div class='ip3-kv'><b>법적상태</b> {patent.get('legal_status', '') or '-'}</div>",
            unsafe_allow_html=True,
        )
    if patent.get("source_url"):
        st.markdown(f"[원문 링크 ↗]({patent['source_url']})")


# ---------------------------------------------------------------------------
# State mutations
# ---------------------------------------------------------------------------
def _toggle_interest(link_id: int, patent: dict) -> None:
    if patent.get("is_interested"):
        db.update_case_patent(link_id, is_interested=0, interest_status="")
    else:
        db.update_case_patent(
            link_id, is_interested=1, interest_status=DEFAULT_INTEREST, is_excluded=0
        )


def _toggle_exclude(link_id: int, patent: dict, pid: int) -> None:
    if patent.get("is_excluded"):
        db.update_case_patent(link_id, is_excluded=0)
    else:
        db.update_case_patent(link_id, is_excluded=1)
        st.session_state.selected_patent_ids.discard(pid)
