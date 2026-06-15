"""전체 상세 페이지 (정밀 검토용)."""
from __future__ import annotations

import streamlit as st

from components import badges, layout
from services import cache_service
from utils import db


def render() -> None:
    pid = st.session_state.get("detail_patent_id")
    return_page = st.session_state.get("detail_return", "review_result")
    if not pid:
        st.info("표시할 특허가 없습니다.")
        return
    patent = db.get_patent(pid)
    if not patent:
        st.warning("특허 정보를 찾을 수 없습니다.")
        return

    top = st.columns([1, 5])
    if top[0].button("← 돌아가기", use_container_width=True):
        layout.goto(return_page)
    top[1].markdown(f"## {patent.get('title','')}")

    st.markdown(
        badges.country(patent.get("country", ""))
        + " &nbsp; "
        + badges.status_pill(patent.get("legal_status", "") or "법적상태 미상"),
        unsafe_allow_html=True,
    )

    details = cache_service.ensure_details(pid)

    layout.section_label("요약")
    st.write(patent.get("abstract", "") or "요약 정보 없음")

    layout.section_label("도면 전체")
    urls = details.get("drawing_urls", [])
    if urls:
        layout.thumbnails(urls, max_show=20)
        st.caption(f"도면 {len(urls)}건 (URL/메타정보 기준, 이미지 파일은 저장하지 않음)")
    else:
        st.caption("도면 정보 없음")

    layout.section_label("청구항 전체")
    st.write(details.get("claims_text", "") or "청구항 정보 없음")

    layout.section_label("서지정보")
    _bibliography(patent)

    case_id = st.session_state.get("current_case_id")
    cp = db.get_case_patent(case_id, pid) if case_id else None
    if cp:
        layout.section_label("검토 메모")
        memo = st.text_area(
            "검토 메모", value=cp.get("memo", "") or "", key=f"pd_memo_{pid}", height=80,
            label_visibility="collapsed",
        )
        if memo != (cp.get("memo", "") or ""):
            db.update_case_patent(cp["link_id"], memo=memo)

    layout.section_label("비교분석 이력")
    _comparison_history(case_id, pid)

    if patent.get("source_url"):
        st.markdown(f"[원문 링크 ↗]({patent['source_url']})")


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
    ]
    cols = st.columns(2)
    half = (len(fields) + 1) // 2
    for col, group in zip(cols, (fields[:half], fields[half:])):
        col.markdown(
            "".join(
                f"<div class='ip3-kv'><b>{k}</b> &nbsp;{v or '-'}</div>" for k, v in group
            ),
            unsafe_allow_html=True,
        )


def _comparison_history(case_id: int | None, pid: int) -> None:
    if not case_id:
        st.caption("비교분석 이력이 없습니다.")
        return
    run = db.get_latest_comparison_run(case_id)
    if not run:
        st.caption("비교분석 이력이 없습니다.")
        return
    results = [r for r in db.get_comparison_results(run["id"]) if r["patent_id"] == pid]
    if not results:
        st.caption("이 특허에 대한 비교분석 이력이 없습니다.")
        return
    r = results[0]
    st.markdown(
        "판단 상태: " + badges.judgment(r.get("judgment_status", "")),
        unsafe_allow_html=True,
    )
    for label, key in [
        ("유사한 점", "similar_points"),
        ("차이점", "different_points"),
        ("확인할 점", "check_points"),
        ("원문 근거", "original_evidence"),
    ]:
        items = r.get(key) or []
        if items:
            st.markdown(f"**{label}**")
            st.markdown(
                "".join(f"<div class='ip3-kv'>• {it}</div>" for it in items),
                unsafe_allow_html=True,
            )
