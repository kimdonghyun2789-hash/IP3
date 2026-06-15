"""Small text helpers shared across IP3."""
from __future__ import annotations

import re

# Korean + Latin word characters
_TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]+")
_KOREAN_STOP = {
    "그리고", "또는", "위한", "통해", "있는", "있다", "하는", "되는", "대한",
    "위해", "이를", "통한", "내부", "외부", "구성", "구조", "방법", "장치",
    "the", "and", "for", "with", "from", "this", "that", "are", "was",
}


def tokenize(text: str) -> list[str]:
    """Return lower-cased word tokens for simple overlap heuristics."""
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def keywords_from_text(text: str, limit: int = 12) -> list[str]:
    """Extract candidate keywords by frequency, dropping common stop words."""
    counts: dict[str, int] = {}
    for tok in tokenize(text):
        if len(tok) <= 1 or tok in _KOREAN_STOP:
            continue
        counts[tok] = counts.get(tok, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [w for w, _ in ordered[:limit]]


def jaccard(a: str, b: str) -> float:
    """Jaccard similarity (0-1) between two texts' token sets."""
    sa = {t for t in tokenize(a) if t not in _KOREAN_STOP}
    sb = {t for t in tokenize(b) if t not in _KOREAN_STOP}
    if not sa or not sb:
        return 0.0
    inter = sa & sb
    union = sa | sb
    return len(inter) / len(union) if union else 0.0


def truncate(text: str, length: int = 160) -> str:
    if not text:
        return ""
    text = text.strip().replace("\n", " ")
    return text if len(text) <= length else text[: length - 1] + "…"


def shared_terms(a: str, b: str, limit: int = 8) -> list[str]:
    """Return notable terms appearing in both texts."""
    sa = [t for t in tokenize(a) if len(t) > 1 and t not in _KOREAN_STOP]
    sb = {t for t in tokenize(b) if t not in _KOREAN_STOP}
    seen: list[str] = []
    for t in sa:
        if t in sb and t not in seen:
            seen.append(t)
        if len(seen) >= limit:
            break
    return seen
