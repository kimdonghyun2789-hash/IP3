"""IP³ — 아이디어 기반 특허 검토 플랫폼.

Streamlit entry point. Uses an in-app router (session-state driven) rather than
Streamlit's automatic multipage navigation, which is disabled in
``.streamlit/config.toml``.
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="IP³ IP Cube",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded",
)

from components import layout, sidebar  # noqa: E402
from pages import (  # noqa: E402
    library,
    new_review,
    patent_detail,
    projects,
    review_cases,
    review_result,
    settings,
)
from utils import db  # noqa: E402

ROUTES = {
    "new_review": new_review.render,
    "review_result": review_result.render,
    "review_cases": review_cases.render,
    "projects": projects.render,
    "library": library.render,
    "settings": settings.render,
    "patent_detail": patent_detail.render,
}


def main() -> None:
    db.init_db()
    layout.init_state()
    layout.inject_css()
    sidebar.render()

    page = st.session_state.get("page", "new_review")
    render = ROUTES.get(page, new_review.render)
    render()


if __name__ == "__main__":
    main()
