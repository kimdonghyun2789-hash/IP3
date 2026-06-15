"""Left navigation sidebar for IP3."""
from __future__ import annotations

import streamlit as st

from components import layout
from utils import config, db


def render() -> None:
    with st.sidebar:
        st.markdown(
            "<div class='ip3-brand'>IP<sup>3</sup></div>"
            "<div class='ip3-brand-sub'>IP CUBE</div>"
            "<div class='ip3-tagline'>"
            "<div><b>I</b>ntellectual Property</div>"
            "<div><b>I</b>dea-to-Patent</div>"
            "<div><b>I</b>ntelligence Platform</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        if st.button("➕  새 검토", use_container_width=True, type="primary", key="nav_new"):
            _start_new_review()

        if st.button("🏠  홈", use_container_width=True, key="nav_home"):
            _start_new_review()

        st.markdown("<div class='ip3-section'>프로젝트</div>", unsafe_allow_html=True)
        projects = db.list_projects()
        for p in projects:
            if st.button(
                f"📁  {p['name']}",
                use_container_width=True,
                key=f"nav_proj_{p['id']}",
            ):
                layout.goto("projects", current_project_id=p["id"])
        if not projects:
            st.caption("아직 프로젝트가 없습니다.")

        if st.button("🗂  검토 케이스", use_container_width=True, key="nav_cases"):
            layout.goto("review_cases")
        if st.button("⭐  보관함", use_container_width=True, key="nav_library"):
            layout.goto("library")

        st.markdown("<div class='ip3-section'>도구</div>", unsafe_allow_html=True)
        if st.button("⚙️  설정", use_container_width=True, key="nav_settings"):
            layout.goto("settings")

        _connection_footer()


def _start_new_review() -> None:
    # Reset the new-review screen to a clean state.
    st.session_state.pending_search = None
    st.session_state.show_completion = False
    st.session_state.completed_case_id = None
    layout.goto("new_review")


def _connection_footer() -> None:
    st.markdown("<hr/>", unsafe_allow_html=True)
    kipris = "연결됨" if config.has_kiprisplus() else "샘플 데이터 모드"
    ai = config.get_ai_provider() if config.has_ai() else "휴리스틱 비교"
    st.caption(f"검색: {kipris}")
    st.caption(f"비교분석: {ai}")
