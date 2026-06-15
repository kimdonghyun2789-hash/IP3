"""Search progress flow and completion card.

This stage performs ONLY similar-patent search + result organisation.
It never runs the AI comparison analysis (that is a separate, user-triggered
step on the results screen).
"""
from __future__ import annotations

import time

import streamlit as st

from analyzers import idea_parser, keyword_expander
from services import cache_service
from utils import db

_STEPS = [
    "아이디어 구조화",
    "검색어 확장",
    "국내 특허 검색",
    "해외 특허 검색",
    "결과 정리",
    "임시저장",
]


def render_progress(params: dict) -> None:
    """Execute the search flow with a visible progress indicator."""
    st.markdown("## 아이디어를 검토하고 있습니다.")
    st.caption("유사특허 검색을 진행 중입니다.")

    bar = st.progress(0.0)
    status_box = st.empty()

    def mark(i: int) -> None:
        status_box.markdown(f"**{i + 1}/{len(_STEPS)}** · {_STEPS[i]} …")
        bar.progress((i + 1) / len(_STEPS))
        time.sleep(0.25)

    # Step 1: structure the idea
    mark(0)
    structure = idea_parser.parse(params["title"], params["description"])

    # Step 2: expand keywords
    mark(1)
    keywords = keyword_expander.expand(
        params["title"], params["description"],
        params.get("keywords", ""), params.get("exclude_keywords", ""),
    )
    keywords_str = ", ".join(keywords)

    # Create the review case (temporary) now that we have structure + keywords.
    case_id = db.create_review_case(
        title=params["title"],
        description=params["description"],
        keywords=keywords_str,
        exclude_keywords=params.get("exclude_keywords", ""),
        search_scope=params.get("search_scope", "국내+해외"),
        top_n=int(params.get("top_n", 20)),
        project_id=params.get("project_id"),
        idea_structure=structure,
        status="임시저장",
        is_temporary=1,
    )
    case = db.get_review_case(case_id)

    # Steps 3-4: search (domestic + foreign handled inside run_search)
    scope = params.get("search_scope", "국내+해외")
    if scope in ("국내", "국내+해외"):
        mark(2)
    if scope in ("해외", "국내+해외"):
        mark(3)
    else:
        bar.progress(4 / len(_STEPS))

    count, source = cache_service.run_search(case_id, case)

    # Step 5: organise
    mark(4)
    # Step 6: temporary save (already temporary in DB)
    mark(5)

    status_box.empty()

    # Hand off to the completion card.
    st.session_state.pending_search = None
    st.session_state.completed_case_id = case_id
    st.session_state.current_case_id = case_id
    st.session_state.search_count = count
    st.session_state.search_source = source
    st.session_state.show_completion = True
    st.session_state.selected_patent_ids = set()
    st.rerun()


def render_completion() -> None:
    """Completion card shown after a search finishes (no auto-navigation)."""
    count = st.session_state.get("search_count", 0)
    source = st.session_state.get("search_source", "")
    case_id = st.session_state.get("completed_case_id")

    with st.container(border=True):
        st.markdown("### ✅ 검토가 완료되었습니다.")
        st.write("유사특허 검색 결과가 준비되었습니다.")
        st.markdown(f"**검색된 특허: {count}건**")
        if source == "sample":
            st.info(
                "샘플 데이터 모드입니다. 실제 검색을 사용하려면 설정에서 "
                "KIPRISPlus API Key를 입력하세요.",
                icon="ℹ️",
            )
        cols = st.columns([1, 1, 4])
        if cols[0].button("결과 보기", type="primary", use_container_width=True):
            st.session_state.show_completion = False
            from components import layout

            layout.goto("review_result", current_case_id=case_id)
        if cols[1].button("닫기", use_container_width=True):
            st.session_state.show_completion = False
            st.rerun()
