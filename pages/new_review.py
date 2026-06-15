"""New review screen — the app's entry point."""
from __future__ import annotations

import streamlit as st

from components import modals, progress
from utils import config, db


def render() -> None:
    # In-progress search or completion card take over the screen.
    if st.session_state.get("pending_search"):
        progress.render_progress(st.session_state.pending_search)
        return
    if st.session_state.get("show_completion"):
        progress.render_completion()
        return
    if st.session_state.get("show_project_modal"):
        modals.project_dialog()

    _render_form()


def _render_form() -> None:
    st.markdown("## 아이디어 기반 특허 검토를 시작하세요.")
    st.caption("아이디어를 입력하면 유사특허를 검색하고, 선택한 특허와의 차이를 정리합니다.")

    if not config.has_kiprisplus():
        st.info(
            "현재 **샘플 데이터 모드**입니다. 실제 검색을 사용하려면 설정에서 "
            "KIPRISPlus API Key를 입력하세요.",
            icon="ℹ️",
        )

    title = st.text_input(
        "아이디어명",
        key="nr_title",
        placeholder="예: PC 중공기둥 배수 슬리브 선매립 구조",
    )
    description = st.text_area(
        "아이디어 설명",
        key="nr_desc",
        height=140,
        placeholder="아이디어의 구조, 목적, 효과를 자유롭게 설명하세요.",
    )

    with st.expander("상세 옵션", expanded=False):
        c1, c2 = st.columns(2)
        scope = c1.radio(
            "검색 범위",
            config.SEARCH_SCOPES,
            index=config.SEARCH_SCOPES.index(config.get("search_scope", "국내+해외"))
            if config.get("search_scope", "국내+해외") in config.SEARCH_SCOPES
            else 2,
            horizontal=True,
            key="nr_scope",
        )
        top_n = c2.radio(
            "결과 수",
            config.TOP_N_OPTIONS,
            index=config.TOP_N_OPTIONS.index(config.get_default_top_n())
            if config.get_default_top_n() in config.TOP_N_OPTIONS
            else 1,
            horizontal=True,
            key="nr_topn",
        )
        keywords = st.text_input(
            "핵심 키워드", key="nr_keywords", placeholder="쉼표로 구분 (선택)"
        )
        exclude = st.text_input(
            "제외어", key="nr_exclude", placeholder="쉼표로 구분 (선택)"
        )

        projects = db.list_projects()
        options = ["(프로젝트 미지정)"] + [p["name"] for p in projects]
        pid_by_name = {p["name"]: p["id"] for p in projects}
        # Preserve a project chosen via the creation modal.
        default_idx = 0
        chosen_pid = st.session_state.get("new_review_project_id")
        if chosen_pid:
            for i, p in enumerate(projects):
                if p["id"] == chosen_pid:
                    default_idx = i + 1
        project_choice = st.selectbox(
            "프로젝트 선택 (선택사항)", options, index=default_idx, key="nr_project"
        )
        project_id = pid_by_name.get(project_choice)

    b1, b2, _ = st.columns([1, 1, 4])
    start = b1.button("검토 시작", type="primary", use_container_width=True)
    if b2.button("➕ 프로젝트", use_container_width=True):
        st.session_state.show_project_modal = True
        st.rerun()

    if start:
        if not title.strip():
            st.warning("아이디어명을 입력하세요.")
            return
        if not description.strip():
            st.warning("아이디어 설명을 입력하세요.")
            return
        st.session_state.pending_search = {
            "title": title.strip(),
            "description": description.strip(),
            "search_scope": scope,
            "top_n": top_n,
            "keywords": keywords.strip(),
            "exclude_keywords": exclude.strip(),
            "project_id": project_id,
        }
        st.session_state.new_review_project_id = None
        st.rerun()
