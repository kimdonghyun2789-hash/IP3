"""Results screen: 3-panel layout with 결과 / 관심특허 / 비교분석 tabs."""
from __future__ import annotations

import streamlit as st

from analyzers import comparison_analyzer
from components import badges, cards, detail_panel, layout, tables
from services import cache_service, report_service
from utils import db

TABS = ["결과", "관심특허", "비교분석"]
INTEREST_STATUSES = ["중요", "확인필요", "참고"]


def render() -> None:
    case_id = st.session_state.get("current_case_id")
    if not case_id:
        st.info("열려 있는 검토 케이스가 없습니다.")
        if st.button("새 검토 시작"):
            layout.goto("new_review")
        return
    case = db.get_review_case(case_id)
    if not case:
        st.warning("검토 케이스를 찾을 수 없습니다.")
        return

    layout.show_flash()
    patents = db.get_case_patents(case_id)

    detail_open = st.session_state.detail_open and st.session_state.detail_patent_id
    if detail_open:
        case_col, results_col, panel_col = st.columns([1.5, 3.4, 2.3])
    else:
        case_col, results_col = st.columns([1.6, 5.4])
        panel_col = None

    with case_col:
        _render_case_panel(case, patents)
    with results_col:
        _render_results_area(case, patents)
    if panel_col is not None:
        with panel_col:
            detail_panel.render()


# ---------------------------------------------------------------------------
# Middle: review case panel
# ---------------------------------------------------------------------------
def _render_case_panel(case: dict, patents: list[dict]) -> None:
    with st.container(border=True):
        st.markdown(
            f"<div class='ip3-patent-title'>📝 {case.get('title','')}</div>",
            unsafe_allow_html=True,
        )
        st.caption(case.get("description", ""))

        layout.section_label("핵심 구성")
        structure = case.get("idea_structure") or {}
        labels = ["적용 대상", "해결 문제", "핵심 구조", "작용 방식", "기대 효과"]
        rows = "".join(
            f"<div class='ip3-kv'><b>{lab}</b> {structure.get(lab,'') or '-'}</div>"
            for lab in labels
        )
        st.markdown(rows, unsafe_allow_html=True)

        layout.section_label("검색 조건")
        st.markdown(
            f"<div class='ip3-kv'><b>검색 범위</b> {case.get('search_scope','')}</div>"
            f"<div class='ip3-kv'><b>결과 수</b> {case.get('top_n','')}</div>"
            f"<div class='ip3-kv'><b>핵심 키워드</b> {case.get('keywords','') or '-'}</div>"
            f"<div class='ip3-kv'><b>제외어</b> {case.get('exclude_keywords','') or '-'}</div>",
            unsafe_allow_html=True,
        )

        layout.section_label("프로젝트")
        projects = db.list_projects()
        opts = ["(프로젝트 미지정)"] + [p["name"] for p in projects]
        name_to_id = {p["name"]: p["id"] for p in projects}
        cur_pid = case.get("project_id")
        cur_idx = 0
        for i, p in enumerate(projects):
            if p["id"] == cur_pid:
                cur_idx = i + 1
        choice = st.selectbox(
            "프로젝트", opts, index=cur_idx, key=f"case_proj_{case['id']}",
            label_visibility="collapsed",
        )
        new_pid = name_to_id.get(choice)
        if new_pid != cur_pid:
            db.update_review_case(case["id"], project_id=new_pid)
            layout.flash("프로젝트가 변경되었습니다.")
            st.rerun()

        layout.section_label("상태")
        if case.get("is_temporary"):
            st.markdown(badges.status_pill("임시저장됨"), unsafe_allow_html=True)
            if st.button("검토 케이스 저장", type="primary", use_container_width=True):
                db.confirm_save_case(case["id"])
                layout.flash("검토 케이스로 저장됨")
                st.rerun()
        else:
            st.markdown(badges.status_pill("검토 케이스로 저장됨"), unsafe_allow_html=True)

        if st.button("재검색", use_container_width=True):
            _research(case)


def _research(case: dict) -> None:
    with st.spinner("유사특허를 다시 검색하고 있습니다…"):
        db.delete_case_patents(case["id"])
        count, source = cache_service.run_search(case["id"], case)
    layout.clear_selection()
    st.session_state.search_source = source
    layout.flash(f"재검색 완료 · {count}건")
    st.rerun()


# ---------------------------------------------------------------------------
# Right: results area with tabs
# ---------------------------------------------------------------------------
def _render_results_area(case: dict, patents: list[dict]) -> None:
    interested = [p for p in patents if p.get("is_interested")]
    run = db.get_latest_comparison_run(case["id"])

    counts = {
        "결과": len([p for p in patents if not p.get("is_excluded")]),
        "관심특허": len(interested),
        "비교분석": len(db.get_comparison_results(run["id"])) if run else 0,
    }
    cols = st.columns(len(TABS))
    for i, tab in enumerate(TABS):
        active = st.session_state.result_tab == tab
        if cols[i].button(
            f"{tab} ({counts[tab]})",
            key=f"tab_{tab}",
            type="primary" if active else "secondary",
            use_container_width=True,
        ):
            st.session_state.result_tab = tab
            st.rerun()

    st.markdown("<hr/>", unsafe_allow_html=True)

    tab = st.session_state.result_tab
    if tab == "결과":
        _render_results_tab(case, patents)
    elif tab == "관심특허":
        _render_interest_tab(case, interested)
    else:
        _render_comparison_tab(case, run)


# ---------------------------------------------------------------------------
# 결과 tab
# ---------------------------------------------------------------------------
def _render_results_tab(case: dict, patents: list[dict]) -> None:
    t = st.columns([1.1, 1.1, 1.1, 2.0])
    view = t[0].segmented_control(
        "보기", ["카드", "목록"], default=st.session_state.result_view, key="rv_view"
    ) or st.session_state.result_view
    st.session_state.result_view = view
    sort = t[1].selectbox(
        "정렬", ["유사도순", "최신순"],
        index=0 if st.session_state.result_sort == "유사도순" else 1, key="rv_sort",
    )
    st.session_state.result_sort = sort
    filt = t[2].selectbox(
        "필터", ["전체", "관심특허", "제외"],
        index=["전체", "관심특허", "제외"].index(st.session_state.result_filter),
        key="rv_filter",
    )
    st.session_state.result_filter = filt

    selected = st.session_state.selected_patent_ids
    t[3].markdown(
        f"<div style='padding-top:26px'>선택: <b>{len(selected)}건</b></div>",
        unsafe_allow_html=True,
    )

    # Action bar
    a = st.columns([1.4, 1.3, 1.0, 0.9])
    do_compare = a[0].button(
        "선택 특허 비교분석", type="primary",
        disabled=len(selected) == 0, use_container_width=True, key="res_compare",
    )
    do_interest = a[1].button(
        "관심특허 등록", disabled=len(selected) == 0,
        use_container_width=True, key="res_interest",
    )
    if a[2].button("선택 해제", disabled=len(selected) == 0,
                   use_container_width=True, key="res_clear"):
        layout.clear_selection()
        st.rerun()
    if a[3].button("리포트", use_container_width=True, key="res_report"):
        _report_shortcut(case)

    if selected:
        with st.expander(f"선택된 특허 {len(selected)}건", expanded=False):
            id_to_p = {p["id"]: p for p in patents}
            for i, pid in enumerate(selected, start=1):
                p = id_to_p.get(pid)
                if p:
                    st.write(f"{i}. {p.get('title','')}")

    if do_interest:
        for pid in list(selected):
            p = next((x for x in patents if x["id"] == pid), None)
            if p and not p.get("is_interested"):
                db.update_case_patent(
                    p["link_id"], is_interested=1, interest_status="참고", is_excluded=0
                )
        layout.flash(f"{len(selected)}건 관심특허 등록")
        st.rerun()

    if do_compare:
        _run_comparison(case, list(selected))

    # Filter + sort
    filtered = _filter_patents(patents, filt)
    filtered = _sort_patents(filtered, sort)

    st.markdown("<hr/>", unsafe_allow_html=True)
    if not filtered:
        st.info("검색 결과가 없습니다. 키워드나 제외어를 조정한 뒤 다시 검색해보세요.")
        return

    if view == "목록":
        tables.render_table(case["id"], filtered, ctx="결과")
    else:
        for p in filtered:
            cards.render_card(case["id"], p, ctx="결과")


def _filter_patents(patents: list[dict], filt: str) -> list[dict]:
    if filt == "관심특허":
        return [p for p in patents if p.get("is_interested") and not p.get("is_excluded")]
    if filt == "제외":
        return [p for p in patents if p.get("is_excluded")]
    return [p for p in patents if not p.get("is_excluded")]


def _sort_patents(patents: list[dict], sort: str) -> list[dict]:
    if sort == "최신순":
        return sorted(patents, key=lambda p: p.get("filing_date", "") or "", reverse=True)
    return sorted(patents, key=lambda p: p.get("similarity_score", 0) or 0, reverse=True)


# ---------------------------------------------------------------------------
# 관심특허 tab
# ---------------------------------------------------------------------------
def _render_interest_tab(case: dict, interested: list[dict]) -> None:
    if not interested:
        st.info("관심특허가 없습니다. 결과 탭에서 별표(☆)를 눌러 관심특허로 등록할 수 있습니다.")
        return

    sub = st.columns([1.2, 1.2, 1.2, 1.2])
    status_filter = sub[0].selectbox(
        "상태", ["전체"] + INTEREST_STATUSES, key="int_status_filter"
    )
    sort = sub[1].selectbox("정렬", ["관심등록순", "유사도순", "최신순"], key="int_sort")

    items = interested
    if status_filter != "전체":
        items = [p for p in items if p.get("interest_status") == status_filter]
    if sort == "유사도순":
        items = sorted(items, key=lambda p: p.get("similarity_score", 0), reverse=True)
    elif sort == "최신순":
        items = sorted(items, key=lambda p: p.get("filing_date", "") or "", reverse=True)

    selected = st.session_state.selected_patent_ids
    if sub[2].button("선택 특허 비교분석", type="primary",
                     disabled=len(selected) == 0, use_container_width=True,
                     key="int_compare"):
        _run_comparison(case, list(selected))

    st.markdown("<hr/>", unsafe_allow_html=True)
    for p in items:
        _render_interest_card(case, p)


def _render_interest_card(case: dict, p: dict) -> None:
    pid = p["id"]
    with st.container(border=True):
        head = st.columns([5.5, 1.5])
        head[0].markdown(
            f"<div class='ip3-patent-title'>{p.get('title','')}</div>"
            + badges.country(p.get("country", "")),
            unsafe_allow_html=True,
        )
        head[1].markdown(
            badges.similarity(p.get("similarity_score", 0)), unsafe_allow_html=True
        )
        ctrl = st.columns([1.6, 1.2, 1.2])
        cur = p.get("interest_status") or "참고"
        new_status = ctrl[0].selectbox(
            "상태", INTEREST_STATUSES,
            index=INTEREST_STATUSES.index(cur) if cur in INTEREST_STATUSES else 2,
            key=f"is_{pid}",
        )
        if new_status != cur:
            db.update_case_patent(p["link_id"], interest_status=new_status)
            st.rerun()
        sel = pid in st.session_state.selected_patent_ids
        if ctrl[1].button("✅ 선택됨" if sel else "☐ 비교대상",
                          key=f"isel_{pid}", use_container_width=True):
            layout.toggle_select(pid)
            st.rerun()
        if ctrl[2].button("관심 해제", key=f"iunstar_{pid}", use_container_width=True):
            db.update_case_patent(p["link_id"], is_interested=0, interest_status="")
            st.rerun()

        memo = st.text_area(
            "검토 메모", value=p.get("memo", "") or "", key=f"imemo_{pid}", height=70,
            placeholder="예: 도면 3 배수구 위치 확인 필요",
        )
        if memo != (p.get("memo", "") or ""):
            db.update_case_patent(p["link_id"], memo=memo)


# ---------------------------------------------------------------------------
# 비교분석 tab
# ---------------------------------------------------------------------------
def _render_comparison_tab(case: dict, run: dict | None) -> None:
    if not run:
        st.info(
            "비교분석할 특허를 선택하세요.\n\n"
            "결과 탭에서 특허를 체크한 뒤 [선택 특허 비교분석]을 실행하면 "
            "내 아이디어와의 유사점과 차이점을 정리합니다.",
            icon="🔎",
        )
        return

    results = db.get_comparison_results(run["id"])
    if not results:
        st.info("비교분석 결과가 없습니다.")
        return

    top = st.columns([2.2, 1.2, 1.2, 1.4])
    top[0].markdown(f"#### 선택 특허 {len(results)}건 비교분석 완료")
    if top[1].button("PDF 리포트 생성", use_container_width=True, key="cmp_pdf"):
        _generate_report(case, "PDF")
    if top[2].button("Excel 내보내기", use_container_width=True, key="cmp_xlsx"):
        _generate_report(case, "Excel")
    if top[3].button("비교분석 다시 실행", use_container_width=True, key="cmp_rerun"):
        ids = [r["patent_id"] for r in results]
        _run_comparison(case, ids)

    _render_report_download()

    # Summary table
    layout.section_label("비교분석 요약")
    head = st.columns([2.6, 2.2, 2.2, 2.0, 1.2])
    for col, label in zip(head, ["특허명", "주요 유사점", "주요 차이점", "확인할 점", "판단 상태"]):
        col.markdown(f"<div class='ip3-section'>{label}</div>", unsafe_allow_html=True)
    for r in results:
        row = st.columns([2.6, 2.2, 2.2, 2.0, 1.2])
        row[0].markdown(
            f"<span class='ip3-meta' style='font-weight:600'>{r.get('title','')}</span>",
            unsafe_allow_html=True,
        )
        row[1].markdown(
            f"<span class='ip3-meta'>{_first(r.get('similar_points'))}</span>",
            unsafe_allow_html=True,
        )
        row[2].markdown(
            f"<span class='ip3-meta'>{_first(r.get('different_points'))}</span>",
            unsafe_allow_html=True,
        )
        row[3].markdown(
            f"<span class='ip3-meta'>{_first(r.get('check_points'))}</span>",
            unsafe_allow_html=True,
        )
        row[4].markdown(badges.judgment(r.get("judgment_status", "")), unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)
    layout.section_label("특허별 상세 비교분석")
    for r in results:
        _render_comparison_card(r)


def _render_comparison_card(r: dict) -> None:
    with st.container(border=True):
        st.markdown(
            f"<div class='ip3-patent-title'>{r.get('title','')}</div>"
            + badges.country(r.get("country", ""))
            + " &nbsp; "
            + badges.judgment(r.get("judgment_status", "")),
            unsafe_allow_html=True,
        )
        st.caption(
            f"{r.get('applicant','')} · "
            f"{r.get('publication_no','') or r.get('application_no','')}"
        )
        _bullet_block("유사한 점", r.get("similar_points"))
        _bullet_block("차이점", r.get("different_points"))
        _bullet_block("확인할 점", r.get("check_points"))
        if r.get("source_locations"):
            layout.section_label("확인 위치")
            st.write(", ".join(r["source_locations"]))
        _bullet_block("원문 근거", r.get("original_evidence"))

        memo = st.text_area(
            "검토 메모", value=r.get("summary_memo", "") or "",
            key=f"cmp_memo_{r['id']}", height=70,
        )
        if memo != (r.get("summary_memo", "") or ""):
            db.update_comparison_memo(r["id"], memo)


def _bullet_block(label: str, items: list[str] | None) -> None:
    layout.section_label(label)
    items = items or []
    if not items:
        st.markdown("<span class='ip3-meta'>- 없음</span>", unsafe_allow_html=True)
        return
    st.markdown(
        "".join(f"<div class='ip3-kv'>• {it}</div>" for it in items),
        unsafe_allow_html=True,
    )


def _first(items: list[str] | None) -> str:
    return items[0] if items else "-"


# ---------------------------------------------------------------------------
# Shared actions
# ---------------------------------------------------------------------------
def _run_comparison(case: dict, ids: list[int]) -> None:
    if not ids:
        return
    with st.spinner(f"선택 특허 {len(ids)}건을 비교분석하고 있습니다…"):
        comparison_analyzer.run_comparison(case, ids)
    st.session_state.result_tab = "비교분석"
    layout.flash(f"비교분석 완료 · {len(ids)}건")
    st.rerun()


def _report_shortcut(case: dict) -> None:
    run = db.get_latest_comparison_run(case["id"])
    if not run or not db.get_comparison_results(run["id"]):
        st.toast(
            "비교분석 결과가 아직 없습니다. 결과 탭에서 특허를 선택한 뒤 "
            "[선택 특허 비교분석]을 실행하세요."
        )
    else:
        st.session_state.result_tab = "비교분석"
        st.rerun()


def _render_report_download() -> None:
    import os

    path = st.session_state.get("last_report_path")
    if not path or not os.path.exists(path):
        return
    fname = os.path.basename(path)
    with open(path, "rb") as fh:
        data = fh.read()
    mime = (
        "application/pdf"
        if fname.lower().endswith(".pdf")
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.download_button(
        f"⬇️ 리포트 다운로드 ({fname})",
        data=data,
        file_name=fname,
        mime=mime,
        key="dl_report",
    )
    st.caption(f"저장 위치: {path}")


def _generate_report(case: dict, report_type: str) -> None:
    try:
        with st.spinner(f"{report_type} 리포트를 생성하고 있습니다…"):
            path = report_service.generate(case["id"], report_type)
        layout.flash(f"{report_type} 리포트 생성 완료")
        st.session_state["last_report_path"] = str(path)
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.error(f"리포트 생성 실패: {exc}")
