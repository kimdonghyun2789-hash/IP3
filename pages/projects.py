"""프로젝트 페이지 (선택사항 구조)."""
from __future__ import annotations

import streamlit as st

from components import badges, layout, modals
from utils import db


def render() -> None:
    layout.show_flash()
    if st.session_state.get("show_project_modal"):
        modals.project_dialog()

    header = st.columns([4, 1.2])
    header[0].markdown("## 프로젝트")
    if header[1].button("➕ 새 프로젝트", use_container_width=True):
        st.session_state.show_project_modal = True
        st.rerun()

    project_id = st.session_state.get("current_project_id")
    project = db.get_project(project_id) if project_id else None

    if project:
        _render_detail(project)
        st.markdown("<hr/>", unsafe_allow_html=True)

    layout.section_label("전체 프로젝트")
    projects = db.list_projects()
    if not projects:
        st.caption("아직 프로젝트가 없습니다. '새 프로젝트'로 생성하세요.")
    for p in projects:
        cases = [c for c in db.list_review_cases() if c.get("project_id") == p["id"]]
        with st.container(border=True):
            row = st.columns([5, 1.2])
            row[0].markdown(
                f"<div class='ip3-patent-title'>📁 {p['name']}</div>"
                f"<span class='ip3-meta'>{p.get('description','') or '설명 없음'} · "
                f"검토 케이스 {len(cases)}건</span>",
                unsafe_allow_html=True,
            )
            if row[1].button("열기", key=f"popen_{p['id']}", use_container_width=True,
                             type="primary"):
                layout.goto("projects", current_project_id=p["id"])


def _render_detail(project: dict) -> None:
    cases = [c for c in db.list_review_cases() if c.get("project_id") == project["id"]]
    interested_total = 0
    for c in cases:
        interested_total += len(
            [x for x in db.get_case_patents(c["id"]) if x.get("is_interested")]
        )

    with st.container(border=True):
        st.markdown(
            f"<div class='ip3-patent-title'>📁 {project['name']}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<span class='ip3-meta'>검토 케이스 {len(cases)}건 · "
            f"관심특허 {interested_total}건 · "
            f"최근 수정 {project.get('updated_at','')[:10]}</span>",
            unsafe_allow_html=True,
        )

        act = st.columns([1.2, 1.4, 1.0])
        if act[0].button("새 검토", key="proj_new", use_container_width=True, type="primary"):
            st.session_state.new_review_project_id = project["id"]
            layout.goto("new_review")
        new_name = act[1].text_input(
            "프로젝트 이름 변경", value=project["name"], key="proj_rename",
            label_visibility="collapsed",
        )
        if new_name and new_name != project["name"]:
            db.update_project(project["id"], name=new_name)
            layout.flash("프로젝트 이름 변경됨")
            st.rerun()
        if act[2].button("삭제", key="proj_del", use_container_width=True):
            db.delete_project(project["id"])
            st.session_state.current_project_id = None
            layout.flash("프로젝트 삭제됨 (케이스는 미지정으로 이동)")
            st.rerun()

        layout.section_label("검토 케이스 목록")
        if not cases:
            st.caption("이 프로젝트에 속한 검토 케이스가 없습니다.")
        for c in cases:
            cc = st.columns([5, 1.2])
            cc[0].markdown(
                f"<span class='ip3-meta' style='font-weight:600'>{c.get('title','')}</span> "
                + badges.status_pill(c.get("status", "")),
                unsafe_allow_html=True,
            )
            if cc[1].button("열기", key=f"pcase_{c['id']}", use_container_width=True):
                layout.clear_selection()
                st.session_state.result_tab = "결과"
                layout.goto("review_result", current_case_id=c["id"])

        memo = st.text_area(
            "프로젝트 메모", value=project.get("memo", "") or "", key="proj_memo", height=80
        )
        if memo != (project.get("memo", "") or ""):
            db.update_project(project["id"], memo=memo)
