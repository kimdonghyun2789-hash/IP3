"""AI provider abstraction for IP3.

The comparison analysis is not tied to a single model. The provider is chosen
in the Settings screen:

    Gemini | OpenAI | Anthropic | Local/Other | 사용 안 함

Each provider's SDK is imported lazily so the app runs even when none are
installed. When no usable provider is configured, callers fall back to the
heuristic analyzer (see ``analyzers.comparison_analyzer``).
"""
from __future__ import annotations

import json
import re

from utils import config

JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class AIError(Exception):
    """Raised when an AI provider call fails."""


def is_available() -> bool:
    """True when a provider other than 'Local/Other' / '사용 안 함' has a key."""
    provider = config.get_ai_provider()
    if provider in ("", "사용 안 함", "Local/Other"):
        return False
    return bool(config.get_ai_key().strip())


# ---------------------------------------------------------------------------
# Provider dispatch
# ---------------------------------------------------------------------------
def generate(prompt: str, system: str = "") -> str:
    """Send a prompt to the configured provider and return raw text output."""
    provider = config.get_ai_provider()
    key = config.get_ai_key().strip()
    if provider in ("", "사용 안 함", "Local/Other"):
        raise AIError("AI Provider가 설정되지 않았습니다.")
    if not key:
        raise AIError("AI API Key가 설정되지 않았습니다.")

    if provider == "OpenAI":
        return _generate_openai(prompt, system, key)
    if provider == "Gemini":
        return _generate_gemini(prompt, system, key)
    if provider == "Anthropic":
        return _generate_anthropic(prompt, system, key)
    raise AIError(f"지원하지 않는 Provider: {provider}")


def _generate_openai(prompt: str, system: str, key: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AIError("openai 패키지가 설치되지 않았습니다. (pip install openai)") from exc
    client = OpenAI(api_key=key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(
        model="gpt-4o-mini", messages=messages, temperature=0.2
    )
    return resp.choices[0].message.content or ""


def _generate_gemini(prompt: str, system: str, key: str) -> str:
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise AIError(
            "google-generativeai 패키지가 설치되지 않았습니다. (pip install google-generativeai)"
        ) from exc
    genai.configure(api_key=key)
    model = genai.GenerativeModel(
        "gemini-1.5-flash", system_instruction=system or None
    )
    resp = model.generate_content(prompt)
    return resp.text or ""


def _generate_anthropic(prompt: str, system: str, key: str) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise AIError("anthropic 패키지가 설치되지 않았습니다. (pip install anthropic)") from exc
    client = anthropic.Anthropic(api_key=key)
    resp = client.messages.create(
        model="claude-3-5-sonnet-latest",
        max_tokens=1500,
        system=system or "",
        messages=[{"role": "user", "content": prompt}],
    )
    parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
    return "".join(parts)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------
def generate_json(prompt: str, system: str = "") -> dict:
    """Generate output and parse the first JSON object found in it."""
    raw = generate(prompt, system)
    return parse_json(raw)


def parse_json(raw: str) -> dict:
    """Extract and parse the first JSON object in a model response."""
    if not raw:
        raise AIError("AI 응답이 비어 있습니다.")
    match = JSON_BLOCK_RE.search(raw)
    if not match:
        raise AIError("AI 응답에서 JSON을 찾을 수 없습니다.")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise AIError(f"AI 응답 JSON 해석 실패: {exc}") from exc


def test_connection() -> tuple[bool, str]:
    """Connectivity check for the Settings screen."""
    provider = config.get_ai_provider()
    if provider in ("", "사용 안 함"):
        return False, "미연결: Provider가 '사용 안 함'입니다."
    if provider == "Local/Other":
        return True, "연결됨: 로컬/휴리스틱 비교분석 사용"
    if not config.get_ai_key().strip():
        return False, "미연결: API Key가 설정되지 않았습니다."
    try:
        out = generate("OK 라고만 답하세요.")
        return (bool(out), "연결됨" if out else "오류: 빈 응답")
    except AIError as exc:
        return False, f"오류: {exc}"
    except Exception as exc:  # pragma: no cover - provider/network dependent
        return False, f"오류: {exc.__class__.__name__}"
