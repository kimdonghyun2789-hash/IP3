"""Parse a free-text idea into the structured fields used in the case panel.

Fields: 적용 대상 / 해결 문제 / 핵심 구조 / 작용 방식 / 기대 효과.

Uses the configured AI provider when available; otherwise produces a minimal
heuristic structure that never invents content the user did not provide.
"""
from __future__ import annotations

from services import ai_client
from utils import prompts, text_utils

STRUCTURE_KEYS = ["적용 대상", "해결 문제", "핵심 구조", "작용 방식", "기대 효과"]


def empty_structure() -> dict:
    return {k: "" for k in STRUCTURE_KEYS}


def parse(title: str, description: str) -> dict:
    """Return a structured representation of the idea."""
    if ai_client.is_available():
        try:
            prompt = prompts.render(
                "idea_parse", title=title, description=description
            )
            data = ai_client.generate_json(prompt)
            structure = empty_structure()
            for key in STRUCTURE_KEYS:
                value = data.get(key, "")
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                structure[key] = str(value).strip()
            return structure
        except ai_client.AIError:
            pass

    # Heuristic fallback: do not fabricate; summarise what we have.
    structure = empty_structure()
    structure["핵심 구조"] = text_utils.truncate(description, 200)
    return structure
