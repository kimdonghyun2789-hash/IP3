"""Lightweight similarity scoring used to rank/annotate results.

This is a deterministic text-overlap heuristic, not an AI model. It is used to
order results when the data source does not provide a relevance score.
"""
from __future__ import annotations

from utils import text_utils


def score(idea_text: str, patent_text: str) -> float:
    """Return a 0-100 similarity score between an idea and a patent text."""
    base = text_utils.jaccard(idea_text, patent_text)
    return round(min(0.99, 0.3 + base) * 100, 1)


def patent_text(patent: dict) -> str:
    return " ".join(
        [
            patent.get("title", ""),
            patent.get("abstract", ""),
            patent.get("claims_text", ""),
        ]
    )
