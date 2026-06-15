"""검토 케이스 목록 페이지."""
from __future__ import annotations

import streamlit as st

from components import badges, layout
from utils import db


def _open_case(case_id: int) -> None:
    layout.clear_selection()
    layout.close_detail()
    st.session_state.result_tab = "결과"
    layout.goto("review_result", current_case_id=case_id)


def _case_metrics(case_id: int) -> tuple[int, int, bool]:
    patents = db.get_case_patents(case_id)
    result_count = len([p for p in patents if not p.get("is_excluded")])
    interested = len([p for p in patents if p.get("is_interested")])
    run = db.get_latest_comparison_run(case_id)
    has_cmp = bool(run and db.get_comparison_results(run["id"]))
    return result_count, interested, has_cmp


def render() -> None:
    layout.show_flash()
    st.markdown("## 검토 케이스")

    projects = {p["id"]: p["name"] for p in db.list_projects()}
    saved = db.list_review_cases(include_temporary=False)
    temporary = db.list_temporary_cases()

    layout.section_label("저장된 케이스")
    if not saved:
        st.caption("저장된 검토 케이스가 없습니다.")
    for case in saved:
        _render_case_row(case, projects, temporary=False)

    st.markdown("<hr/>", unsafe_allow_html=True)
    with st.expander(f"임시저장 {len(temporary)}건", expanded=bool(temporary) and not saved):
        if not temporary:
            st.caption("임시저장된 케이스가 없습니다.")
        for case in temporary:
            _render_case_row(case, projects, temporary=True)


def _render_case_row(case: dict, projects: dict, temporary: bool) -> None:
    rc, interested, has_cmp = _case_metrics(case["id"])
    with st.container(border=True):
        info, actions = st.columns([5.0, 2.2])
        with info:
            st.markdown(
                f"<div class='ip3-patent-title'>{case.get('title','(제목 없음)')}</div>",
                unsafe_allow_html=True,
            )
            proj = projects.get(case.get("project_id"), "프로젝트 미지정")
            st.markdown(
                f"<span class='ip3-meta'>{proj} · {case.get('search_scope','')} · "
                f"결과 {rc}건 · 관심 {interested}건 · "
                f"비교분석 {'완료' if has_cmp else '미실행'}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                badges.status_pill(case.get("status", ""))
                + f" <span class='ip3-meta'>생성 {case.get('created_at','')[:10]} · "
                f"수정 {case.get('updated_at','')[:10]}</span>",
                unsafe_allow_html=True,
            )
        with actions:
            if st.button("열기", key=f"open_{case['id']}", use_container_width=True,
                         type="primary"):
                _open_case(case["id"])
            if temporary:
                if st.button("저장", key=f"save_{case['id']}", use_container_width=True):
                    db.confirm_save_case(case["id"])
                    layout.flash("검토 케이스로 저장됨")
                    st.rerun()
            if st.button("삭제", key=f"del_{case['id']}", use_container_width=True):
                db.delete_review_case(case["id"])
                layout.flash("검토 케이스 삭제됨")
                st.rerun()
