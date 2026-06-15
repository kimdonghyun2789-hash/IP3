"""Global layout: CSS, session-state defaults, and navigation helpers."""
from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
_DEFAULTS = {
    "page": "new_review",
    "current_case_id": None,
    "detail_patent_id": None,
    "detail_tab": "요약",
    "detail_open": False,
    "result_tab": "결과",
    "result_view": "카드",
    "result_sort": "유사도순",
    "result_filter": "전체",
    "selected_patent_ids": set(),
    "pending_search": None,
    "completed_case_id": None,
    "search_count": 0,
    "search_source": "",
    "show_completion": False,
    "show_project_modal": False,
    "library_status_filter": "전체",
    "current_project_id": None,
    "flash": None,
}


def init_state() -> None:
    for key, value in _DEFAULTS.items():
        if key not in st.session_state:
            # copy mutable defaults
            st.session_state[key] = set() if isinstance(value, set) else value


def goto(page: str, **params) -> None:
    st.session_state.page = page
    for key, value in params.items():
        st.session_state[key] = value
    st.rerun()


def set_result_tab(tab: str) -> None:
    st.session_state.result_tab = tab


def toggle_select(patent_id: int) -> None:
    sel = st.session_state.selected_patent_ids
    if patent_id in sel:
        sel.discard(patent_id)
    else:
        sel.add(patent_id)


def clear_selection() -> None:
    st.session_state.selected_patent_ids = set()


def open_detail(patent_id: int, tab: str = "요약") -> None:
    st.session_state.detail_patent_id = patent_id
    st.session_state.detail_tab = tab
    st.session_state.detail_open = True


def close_detail() -> None:
    st.session_state.detail_open = False
    st.session_state.detail_patent_id = None


def flash(message: str) -> None:
    st.session_state.flash = message


def show_flash() -> None:
    msg = st.session_state.get("flash")
    if msg:
        st.toast(msg)
        st.session_state.flash = None


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
CSS = """
<style>
:root {
  --ip3-primary:#2563EB; --ip3-primary-dark:#1d4ed8;
  --ip3-bg:#FFFFFF; --ip3-soft:#F4F6FB; --ip3-border:#dbe2ea;
  --ip3-text:#1F2933; --ip3-muted:#627084;
}
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 100%; }
#MainMenu, footer { visibility: hidden; }

/* Brand mark in sidebar */
.ip3-brand { font-size: 26px; font-weight: 800; letter-spacing:-.5px;
  color: var(--ip3-primary); margin: 2px 0 2px 2px; }
.ip3-brand span { font-size: 15px; vertical-align: super; }
.ip3-tagline { font-size: 11px; color: var(--ip3-muted); margin: 0 0 10px 3px; }

/* Sidebar */
section[data-testid="stSidebar"] { background: var(--ip3-soft);
  border-right: 1px solid var(--ip3-border); }
section[data-testid="stSidebar"] .stButton > button {
  text-align: left; justify-content: flex-start; background: transparent;
  border: none; color: var(--ip3-text); font-weight: 500; padding: 6px 10px;
  border-radius: 8px; }
section[data-testid="stSidebar"] .stButton > button:hover {
  background: #e7edf7; color: var(--ip3-primary-dark); }

/* Buttons */
.stButton > button { border-radius: 8px; border: 1px solid var(--ip3-border);
  font-weight: 600; }
.stButton > button[kind="primary"] { background: var(--ip3-primary);
  border-color: var(--ip3-primary); }
.stButton > button[kind="primary"]:hover { background: var(--ip3-primary-dark); }

/* Bordered containers act as cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: 12px; border-color: var(--ip3-border) !important; }

/* Headings */
h1, h2, h3 { color: var(--ip3-text); }
.ip3-section { font-size: 12px; font-weight: 700; letter-spacing:.4px;
  color: var(--ip3-muted); text-transform: uppercase; margin: 4px 0 6px; }
.ip3-patent-title { font-size: 15px; font-weight: 700; color: var(--ip3-text);
  line-height: 1.35; }
.ip3-meta { font-size: 12px; color: var(--ip3-muted); }

/* Drawing thumbnails */
.ip3-thumbs { display:flex; gap:6px; flex-wrap:wrap; margin:8px 0 4px; }
.ip3-thumb { width:74px; height:60px; border:1px solid var(--ip3-border);
  border-radius:8px; background:linear-gradient(135deg,#f7f9fc,#eef2f8);
  display:flex; align-items:center; justify-content:center; font-size:10px;
  color:var(--ip3-muted); text-align:center; }
.ip3-thumb.more { background:#eef2f8; font-weight:700; color:var(--ip3-primary-dark); }

/* Detail panel */
.ip3-panel { border-left: 3px solid var(--ip3-primary); }

/* Misc */
hr { margin: 0.6rem 0; }
.ip3-kv { font-size:12.5px; color:var(--ip3-text); margin:2px 0; }
.ip3-kv b { color:var(--ip3-muted); font-weight:600; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def section_label(text: str) -> None:
    st.markdown(f"<div class='ip3-section'>{text}</div>", unsafe_allow_html=True)


def thumbnails(drawing_urls: list[str], max_show: int = 5) -> None:
    """Render drawing thumbnails as offline-safe placeholder tiles.

    Per the cache policy, only drawing URLs/metadata are stored (never image
    binaries), so thumbnails are represented as labelled tiles.
    """
    count = len(drawing_urls)
    if count == 0:
        return
    tiles = []
    for i in range(min(count, max_show)):
        tiles.append(f"<div class='ip3-thumb'>도면 {i + 1}</div>")
    if count > max_show:
        tiles.append(f"<div class='ip3-thumb more'>+{count - max_show}</div>")
    st.markdown(
        "<div class='ip3-thumbs'>" + "".join(tiles) + "</div>",
        unsafe_allow_html=True,
    )
