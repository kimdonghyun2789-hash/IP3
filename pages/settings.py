"""설정 화면: API / 검색 / AI / 데이터 관리."""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

import streamlit as st

from components import layout
from services import ai_client, cache_service, kiprisplus_client
from utils import config, db


def render() -> None:
    layout.show_flash()
    st.markdown("## 설정")
    tab_api, tab_search, tab_ai, tab_data = st.tabs(
        ["API 설정", "검색 설정", "AI 설정", "데이터 관리"]
    )
    with tab_api:
        _api_settings()
    with tab_search:
        _search_settings()
    with tab_ai:
        _ai_settings()
    with tab_data:
        _data_settings()


# ---------------------------------------------------------------------------
def _api_settings() -> None:
    st.caption("KIPRISPlus API Key는 특허 검색 및 상세정보 조회에 사용됩니다.")
    st.caption("AI API Key는 'AI 설정' 탭에서 입력합니다.")

    kipris = st.text_input(
        "KIPRISPlus API Key", value=config.get("kiprisplus_api_key", ""),
        type="password", key="set_kipris",
    )

    cols = st.columns([1, 1, 4])
    if cols[0].button("저장", type="primary", key="api_save"):
        config.set("kiprisplus_api_key", kipris.strip())
        layout.flash("KIPRISPlus API Key 저장됨")
        st.rerun()
    if cols[1].button("연결 테스트", key="api_test"):
        with st.spinner("연결을 확인하고 있습니다…"):
            k_ok, k_msg = kiprisplus_client.test_connection()
        st.markdown(f"**KIPRISPlus:** {'🟢' if k_ok else '🔴'} {k_msg}")

    st.markdown("<hr/>", unsafe_allow_html=True)
    k_state = "🟢 키 입력됨" if config.has_kiprisplus() else "⚪ 미입력 (샘플 데이터 모드)"
    a_state = "🟢 키 입력됨" if config.has_ai() else "⚪ 미입력 (휴리스틱 비교)"
    st.markdown(f"**KIPRISPlus:** {k_state}")
    st.markdown(f"**AI Provider:** {a_state}  ·  키 입력은 'AI 설정' 탭")
    st.caption("실제 연결 가능 여부는 위의 **연결 테스트**(KIPRISPlus), 'AI 설정' 탭의 **연결 테스트**(AI)로 확인하세요.")


def _search_settings() -> None:
    scope = st.radio(
        "기본 검색 범위", config.SEARCH_SCOPES,
        index=config.SEARCH_SCOPES.index(config.get("search_scope", "국내+해외"))
        if config.get("search_scope", "국내+해외") in config.SEARCH_SCOPES else 2,
        horizontal=True, key="set_scope",
    )
    top_n = st.radio(
        "기본 결과 수", config.TOP_N_OPTIONS,
        index=config.TOP_N_OPTIONS.index(config.get_default_top_n())
        if config.get_default_top_n() in config.TOP_N_OPTIONS else 1,
        horizontal=True, key="set_topn",
    )
    sort = st.radio(
        "기본 정렬", config.SORT_OPTIONS,
        index=config.SORT_OPTIONS.index(config.get("default_sort", "유사도순"))
        if config.get("default_sort", "유사도순") in config.SORT_OPTIONS else 0,
        horizontal=True, key="set_sort",
    )
    if st.button("저장", type="primary", key="search_save"):
        config.set("search_scope", scope)
        config.set("top_n", str(top_n))
        config.set("default_sort", sort)
        layout.flash("검색 설정 저장됨")
        st.rerun()


def _ai_settings() -> None:
    provider = st.selectbox(
        "AI Provider", config.AI_PROVIDERS,
        index=config.AI_PROVIDERS.index(config.get_ai_provider())
        if config.get_ai_provider() in config.AI_PROVIDERS else 4,
        key="set_provider",
    )
    ai_key = st.text_input(
        "AI API Key", value=config.get("ai_api_key", ""), type="password", key="set_aikey2",
    )
    ai_model = st.text_input(
        "AI 모델 (선택)", value=config.get("ai_model", ""), key="set_aimodel",
        placeholder="비워두면 권장 모델 자동 사용 (예: gemini-2.0-flash, gpt-4o-mini)",
    )

    layout.section_label("비교분석 기본 항목")
    fields = ["유사한 점", "차이점", "확인할 점", "확인 위치", "원문 근거", "판단 상태"]
    current = config.get("ai_fields", ",".join(fields)).split(",")
    chosen = []
    for fld in fields:
        if st.checkbox(fld, value=fld in current, key=f"aif_{fld}"):
            chosen.append(fld)

    cols = st.columns([1, 1, 4])
    if cols[0].button("저장", type="primary", key="ai_save"):
        config.set("ai_provider", provider)
        config.set("ai_api_key", ai_key.strip())
        config.set("ai_model", ai_model.strip())
        config.set("ai_fields", ",".join(chosen))
        layout.flash("AI 설정 저장됨")
        st.rerun()
    if cols[1].button("연결 테스트", key="ai_test"):
        with st.spinner("연결을 확인하고 있습니다…"):
            ok, msg = ai_client.test_connection()
        st.markdown(f"**AI Provider:** {'🟢' if ok else '🔴'} {msg}")
    st.caption(
        "Provider가 'Local/Other' 또는 '사용 안 함'이면 비교분석은 내장 휴리스틱으로 동작합니다."
    )


def _data_settings() -> None:
    usage = cache_service.cache_usage()
    report_dir = config.get_report_dir()

    st.markdown(
        f"<div class='ip3-kv'><b>DB 위치</b> {db.DB_PATH}</div>"
        f"<div class='ip3-kv'><b>리포트 저장 폴더</b> {report_dir}</div>"
        f"<div class='ip3-kv'><b>캐시 사용량</b> 특허 {usage['patents']}건 · "
        f"상세 캐시 {usage['detail_rows']}건</div>"
        f"<div class='ip3-kv'><b>임시저장 케이스</b> {usage['temporary_cases']}건</div>",
        unsafe_allow_html=True,
    )

    thumb = config.get("cache_thumbnails", "0") == "1"
    new_thumb = st.toggle("도면 썸네일 임시 저장", value=thumb, key="set_thumb")
    if new_thumb != thumb:
        config.set("cache_thumbnails", "1" if new_thumb else "0")
        st.rerun()
    st.caption("기본 OFF. 도면 이미지 파일 자체는 저장하지 않으며 URL/메타정보만 캐시합니다.")

    st.markdown("<hr/>", unsafe_allow_html=True)
    cols = st.columns(4)
    if cols[0].button("리포트 폴더 경로", use_container_width=True):
        st.code(str(report_dir))
    if cols[1].button("캐시 정리", use_container_width=True):
        n = db.clear_cache()
        layout.flash(f"상세 캐시 {n}건 정리됨")
        st.rerun()
    if cols[2].button("임시저장 삭제", use_container_width=True):
        n = db.delete_temporary_cases()
        layout.flash(f"임시저장 {n}건 삭제됨")
        st.rerun()
    if cols[3].button("DB 백업", use_container_width=True, type="primary"):
        _backup_db(report_dir)


def _backup_db(report_dir: Path) -> None:
    if not db.DB_PATH.exists():
        st.warning("백업할 DB 파일이 없습니다.")
        return
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = report_dir / f"ip3_backup_{stamp}.db"
    shutil.copy2(db.DB_PATH, dest)
    with open(dest, "rb") as fh:
        st.download_button(
            "⬇️ 백업 파일 다운로드", data=fh.read(), file_name=dest.name,
            mime="application/octet-stream", key="dl_backup",
        )
    st.success(f"DB 백업 생성됨: {dest}")
