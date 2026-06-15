"""Expand a user's idea into search keywords.

Uses the configured AI provider when available; otherwise falls back to a
frequency-based keyword extraction (no fabrication).
"""
from __future__ import annotations

from services import ai_client
from utils import prompts, text_utils


def expand(title: str, description: str, keywords: str = "", exclude: str = "") -> list[str]:
    """Return a list of search keywords for the idea."""
    user_keywords = [k.strip() for k in keywords.split(",") if k.strip()]

    if ai_client.is_available():
        try:
            prompt = prompts.render(
                "keyword_expand",
                title=title,
                description=description,
                keywords=keywords or "(없음)",
                exclude_keywords=exclude or "(없음)",
            )
            data = ai_client.generate_json(prompt)
            collected: list[str] = list(user_keywords)
            for field in ("core_keywords", "synonyms", "english_keywords"):
                for kw in data.get(field, []) or []:
                    if kw and kw not in collected:
                        collected.append(kw)
            if collected:
                return collected
        except ai_client.AIError:
            pass

    # Heuristic fallback
    auto = text_utils.keywords_from_text(f"{title} {description}", limit=10)
    merged = list(user_keywords)
    for kw in auto:
        if kw not in merged:
            merged.append(kw)
    return merged
