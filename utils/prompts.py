"""Prompt template loading for IP3.

Templates live in the ``prompts/`` directory as Markdown files. Placeholders use
``{name}`` syntax. ``render`` fills them while leaving JSON examples untouched
(JSON blocks use ``{ ... }`` so we substitute by explicit keys, not str.format).
"""
from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_CACHE: dict[str, str] = {}


def load(name: str) -> str:
    """Load a prompt template by file stem (e.g. ``comparison_analysis``)."""
    if name in _CACHE:
        return _CACHE[name]
    path = PROMPTS_DIR / f"{name}.md"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    _CACHE[name] = text
    return text


def render(name: str, **values) -> str:
    """Render a template, replacing ``{key}`` placeholders by exact match.

    We avoid ``str.format`` so the JSON examples (which contain braces) survive.
    """
    text = load(name)
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text
