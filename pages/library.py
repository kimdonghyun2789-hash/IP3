"""보관함 — 전체 케이스의 관심특허 라이브러리."""
from __future__ import annotations

import streamlit as st

from components import badges, layout
from utils import db, text_utils

INTEREST_STATUSES = ["중요", "확인필요", "참고"]


def render() -> None:
    layout.show_flash()
    st.markdown("## 보관함")
    st.caption("전체 프로젝트·검토 케이스에서 관심 등록한 특허 모음입니다.")

    items = db.list_library_patents()
    if not items:
        st.info("보관된 관심특허가 없습니다. 검토 결과에서 별표(☆)로 관심특허를 등록하세요.")
        return

    f = st.columns([1.2, 1.6, 1.4, 1.2])
    status_filter = f[0].selectbox("상태", ["전체"] + INTEREST_STATUSES, key="lib_status")
    projects = sorted({i.get("project_name") or "미지정" for i in items})
    project_filter = f[1].selectbox("프로젝트", ["전체"] + projects, key="lib_proj")
    countries = sorted({i.get("country") or "" for i in items})
    country_filter = f[2].selectbox("국가", ["전체"] + countries, key="lib_country")
    sort = f[3].selectbox("정렬", ["최근 등록순", "유사도순", "출원일순"], key="lib_sort")

    filtered = items
    if status_filter != "전체":
        filtered = [i for i in filtered if i.get("interest_status") == status_filter]
    if project_filter != "전체":
        filtered = [
            i for i in filtered if (i.get("project_name") or "미지정") == project_filter
        ]
    if country_filter != "전체":
        filtered = [i for i in filtered if (i.get("country") or "") == country_filter]
    if sort == "유사도순":
        filtered = sorted(filtered, key=lambda i: i.get("similarity_score", 0), reverse=True)
    elif sort == "출원일순":
        filtered = sorted(
            filtered, key=lambda i: i.get("filing_date", "") or "", reverse=True
        )

    st.markdown(f"<span class='ip3-meta'>총 {len(filtered)}건</span>", unsafe_allow_html=True)
    st.markdown("<hr/>", unsafe_allow_html=True)
    for item in filtered:
        _render_library_card(item)


def _render_library_card(item: dict) -> None:
    pid = item["id"]
    link_id = item["link_id"]
    with st.container(border=True):
        head = st.columns([5.0, 1.6])
        head[0].markdown(
            f"<div class='ip3-patent-title'>{item.get('title','')}</div>"
            + badges.country(item.get("country", ""))
            + " "
            + badges.interest(item.get("interest_status", "")),
            unsafe_allow_html=True,
        )
        head[1].markdown(
            badges.similarity(item.get("similarity_score", 0)), unsafe_allow_html=True
        )
        st.markdown(
            f"<span class='ip3-meta'>{item.get('applicant','') or '출원인 미상'} · "
            f"출원일 {item.get('filing_date','') or '-'} · "
            f"케이스: {item.get('case_title','')} · "
            f"프로젝트: {item.get('project_name') or '미지정'}</span>",
            unsafe_allow_html=True,
        )

        details = db.get_patent_details(pid) or {}
        layout.thumbnails((details.get("drawing_meta", {}) or {}).get("drawing_urls", []))

        ctrl = st.columns([1.5, 1.4, 1.3, 1.3])
        cur = item.get("interest_status") or "참고"
        new_status = ctrl[0].selectbox(
            "상태", INTEREST_STATUSES,
            index=INTEREST_STATUSES.index(cur) if cur in INTEREST_STATUSES else 2,
            key=f"lib_is_{link_id}",
        )
        if new_status != cur:
            db.update_case_patent(link_id, interest_status=new_status)
            st.rerun()
        if ctrl[1].button("케이스에서 열기", key=f"lib_open_{link_id}",
                          use_container_width=True):
            layout.clear_selection()
            st.session_state.result_tab = "결과"
            layout.goto("review_result", current_case_id=item["review_case_id"])
        if ctrl[2].button("전체 보기", key=f"lib_full_{link_id}", use_container_width=True):
            st.session_state.current_case_id = item["review_case_id"]
            layout.goto("patent_detail", detail_patent_id=pid, detail_return="library")
        if ctrl[3].button("보관 해제", key=f"lib_unstar_{link_id}",
                          use_container_width=True):
            db.update_case_patent(link_id, is_interested=0, interest_status="")
            layout.flash("보관 해제됨")
            st.rerun()

        memo = st.text_area(
            "검토 메모", value=item.get("memo", "") or "", key=f"lib_memo_{link_id}",
            height=60,
        )
        if memo != (item.get("memo", "") or ""):
            db.update_case_patent(link_id, memo=memo)
