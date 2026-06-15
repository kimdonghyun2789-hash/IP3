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
  --ip3-font:"Pretendard","Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",
    "Segoe UI",-apple-system,sans-serif;
}

/* Consistent base typography (icons are preserved below) */
html, body, .stApp, .stMarkdown, .stMarkdown p,
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"],
.stRadio, .stButton button, .stDownloadButton button, h1, h2, h3, h4,
section[data-testid="stSidebar"] {
  font-family: var(--ip3-font);
}
/* Do NOT override Material/icon fonts (fixes 'keyboard_double_arrow' text) */
[data-testid="stIconMaterial"], .material-icons, .material-icons-outlined,
.material-symbols-rounded, .material-symbols-outlined {
  font-family: 'Material Symbols Rounded','Material Symbols Outlined',
    'Material Icons','Material Icons Outlined' !important;
}
.stApp { color: var(--ip3-text); }
.stMarkdown p { font-size: 14px; line-height: 1.6; margin-bottom: .35rem; }
.block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 100%; }
#MainMenu, footer { visibility: hidden; }

/* Headings - uniform scale */
h1 { font-size: 26px !important; font-weight: 800 !important; }
h2 { font-size: 20px !important; font-weight: 700 !important; margin: .2rem 0 .6rem !important; }
h3 { font-size: 16px !important; font-weight: 700 !important; }
h4 { font-size: 14.5px !important; font-weight: 700 !important; }
h1, h2, h3, h4 { color: var(--ip3-text); letter-spacing: -.2px; }
.stCaption, [data-testid="stCaptionContainer"] p {
  font-size: 12.5px !important; color: var(--ip3-muted) !important; line-height: 1.5; }

/* Brand mark in sidebar */
.ip3-brand { font-size: 30px; font-weight: 800; letter-spacing:-.5px;
  color: var(--ip3-primary); margin: 6px 0 0 2px; line-height: 1; }
.ip3-brand sup { font-size: 17px; font-weight: 800; top: -.5em; }
.ip3-brand-sub { font-size: 11px; font-weight: 700; letter-spacing: 3px;
  color: var(--ip3-muted); margin: 5px 0 12px 3px; }
.ip3-tagline { margin: 0 0 14px 3px;
  border-left: 2px solid var(--ip3-border); padding-left: 9px; }
.ip3-tagline div { font-size: 11.5px; color: var(--ip3-muted); line-height: 1.75; }
.ip3-tagline b { color: var(--ip3-text); font-weight: 600; }

/* Sidebar */
section[data-testid="stSidebar"] { background: var(--ip3-soft);
  border-right: 1px solid var(--ip3-border); }
section[data-testid="stSidebar"] .stButton > button {
  text-align: left; justify-content: flex-start; background: transparent;
  border: none; color: var(--ip3-text); font-weight: 500; padding: 6px 10px;
  border-radius: 8px; min-height: 36px; }
section[data-testid="stSidebar"] .stButton > button:hover {
  background: #e7edf7; color: var(--ip3-primary-dark); }

/* Buttons - uniform height + no wrapping */
.stButton > button { border-radius: 8px; border: 1px solid var(--ip3-border);
  font-weight: 600; font-size: 13px; min-height: 38px; padding: 4px 10px;
  white-space: nowrap; }
.stButton > button[kind="primary"] { background: var(--ip3-primary);
  border-color: var(--ip3-primary); }
.stButton > button[kind="primary"]:hover { background: var(--ip3-primary-dark); }

/* Bordered containers act as cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: 12px; border-color: var(--ip3-border) !important; }

/* Reusable text classes */
.ip3-section { font-size: 11.5px; font-weight: 700; letter-spacing:.4px;
  color: var(--ip3-muted); text-transform: uppercase; margin: 10px 0 5px; }
.ip3-patent-title { font-size: 15px; font-weight: 700; color: var(--ip3-text);
  line-height: 1.4; margin-bottom: 3px; overflow-wrap: anywhere; word-break: break-word; }
.ip3-meta { font-size: 12.5px; color: var(--ip3-muted); line-height: 1.55;
  overflow-wrap: anywhere; }
.ip3-kv { font-size: 13px; color: var(--ip3-text); margin: 3px 0; line-height: 1.55;
  overflow-wrap: anywhere; }
.ip3-kv b { color: var(--ip3-muted); font-weight: 600; margin-right: 4px; }

/* Drawing thumbnails */
.ip3-thumbs { display:flex; gap:6px; flex-wrap:wrap; margin:8px 0 4px; }
.ip3-thumb { width:72px; height:58px; border:1px solid var(--ip3-border);
  border-radius:8px; background:linear-gradient(135deg,#f7f9fc,#eef2f8);
  display:flex; align-items:center; justify-content:center; font-size:10.5px;
  color:var(--ip3-muted); text-align:center; }
.ip3-thumb.more { background:#eef2f8; font-weight:700; color:var(--ip3-primary-dark); }

/* Detail panel */
.ip3-panel { border-left: 3px solid var(--ip3-primary); }

/* Misc */
hr { margin: 0.7rem 0; border-color: var(--ip3-border); }
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
