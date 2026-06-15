"""Small HTML badge / chip helpers for IP3.

All functions return HTML strings to be rendered via
``st.markdown(..., unsafe_allow_html=True)``.
"""
from __future__ import annotations

INTEREST_COLORS = {
    "중요": ("#fde8e8", "#c81e1e"),
    "확인필요": ("#fdf3d8", "#9a6700"),
    "참고": ("#e6f0fb", "#1d4ed8"),
}

JUDGMENT_COLORS = {
    "명확": ("#dcfce7", "#15803d"),
    "부분확인": ("#e0ecff", "#1d4ed8"),
    "추정": ("#fdf3d8", "#9a6700"),
    "확인필요": ("#eef1f5", "#52606d"),
}

COUNTRY_LABELS = {
    "KR": "🇰🇷 KR",
    "US": "🇺🇸 US",
    "CN": "🇨🇳 CN",
    "JP": "🇯🇵 JP",
    "EP": "🇪🇺 EP",
    "": "🌐 —",
}


def _chip(text: str, bg: str, fg: str) -> str:
    return (
        f"<span style='display:inline-block;padding:1px 9px;border-radius:11px;"
        f"font-size:11px;font-weight:600;background:{bg};color:{fg};"
        f"white-space:nowrap'>{text}</span>"
    )


def interest(status: str) -> str:
    if not status:
        return ""
    bg, fg = INTEREST_COLORS.get(status, ("#eef1f5", "#52606d"))
    return _chip(status, bg, fg)


def judgment(status: str) -> str:
    bg, fg = JUDGMENT_COLORS.get(status, ("#eef1f5", "#52606d"))
    return _chip(status, bg, fg)


def country(code: str) -> str:
    label = COUNTRY_LABELS.get((code or "").upper(), f"🌐 {code}")
    return _chip(label, "#eef2f7", "#334e68")


def similarity(score: float) -> str:
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0.0
    if score >= 80:
        bg, fg = "#dcfce7", "#15803d"
    elif score >= 60:
        bg, fg = "#e0ecff", "#1d4ed8"
    elif score >= 40:
        bg, fg = "#fdf3d8", "#9a6700"
    else:
        bg, fg = "#eef1f5", "#52606d"
    return _chip(f"유사도 {score:.0f}", bg, fg)


def status_pill(text: str) -> str:
    return _chip(text, "#eef2f7", "#334e68")
