"""Modal dialogs for IP3 (project creation)."""
from __future__ import annotations

import streamlit as st

from utils import db


@st.dialog("새 프로젝트")
def project_dialog() -> None:
    name = st.text_input("프로젝트명", key="modal_proj_name")
    description = st.text_area("설명", key="modal_proj_desc", placeholder="선택 입력")
    cols = st.columns(2)
    if cols[0].button("생성", type="primary", use_container_width=True):
        if not name.strip():
            st.warning("프로젝트명을 입력하세요.")
        else:
            pid = db.create_project(name.strip(), description.strip())
            st.session_state.show_project_modal = False
            st.session_state.new_review_project_id = pid
            st.rerun()
    if cols[1].button("취소", use_container_width=True):
        st.session_state.show_project_modal = False
        st.rerun()
