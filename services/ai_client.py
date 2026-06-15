"""AI provider abstraction for IP3.

The comparison analysis is not tied to a single model. The provider is chosen
in the Settings screen:

    Gemini | OpenAI | Anthropic | Local/Other | 사용 안 함

Each provider's SDK is imported lazily so the app runs even when none are
installed. **Any** provider/network failure is converted to ``AIError`` so the
callers can fall back to the heuristic analyzer (see
``analyzers.comparison_analyzer``) instead of crashing the app.
"""
from __future__ import annotations

import json
import re

from utils import config

JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

# Current, widely-available default models per provider.
DEFAULT_MODELS = {
    "OpenAI": "gpt-4o-mini",
    "Gemini": "gemini-2.0-flash",
    "Anthropic": "claude-3-5-sonnet-latest",
}

# Gemini candidates tried (in order) when discovering a working model.
_GEMINI_CANDIDATES = [
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-1.5-flash-latest",
]
_GEMINI_RESOLVED: str | None = None


class AIError(Exception):
    """Raised when an AI provider call fails (for any reason)."""


def is_available() -> bool:
    """True when a provider other than 'Local/Other' / '사용 안 함' has a key."""
    provider = config.get_ai_provider()
    if provider in ("", "사용 안 함", "Local/Other"):
        return False
    return bool(config.get_ai_key().strip())


def _model_for(provider: str) -> str:
    """Return the configured model override, or the provider default."""
    override = config.get("ai_model", "").strip()
    return override or DEFAULT_MODELS.get(provider, "")


# ---------------------------------------------------------------------------
# Provider dispatch
# ---------------------------------------------------------------------------
def generate(prompt: str, system: str = "", json_mode: bool = False) -> str:
    """Send a prompt to the configured provider and return raw text output.

    Any underlying error is wrapped in ``AIError``.
    """
    provider = config.get_ai_provider()
    key = config.get_ai_key().strip()
    if provider in ("", "사용 안 함", "Local/Other"):
        raise AIError("AI Provider가 설정되지 않았습니다.")
    if not key:
        raise AIError("AI API Key가 설정되지 않았습니다.")

    try:
        if provider == "OpenAI":
            return _generate_openai(prompt, system, key, json_mode)
        if provider == "Gemini":
            return _generate_gemini(prompt, system, key, json_mode)
        if provider == "Anthropic":
            return _generate_anthropic(prompt, system, key)
    except AIError:
        raise
    except Exception as exc:  # convert every provider/network error to AIError
        raise AIError(f"{provider} 호출 실패: {_short(exc)}") from exc
    raise AIError(f"지원하지 않는 Provider: {provider}")


def _short(exc: Exception) -> str:
    msg = str(exc).strip().replace("\n", " ")
    return (msg[:200] + "…") if len(msg) > 200 else (msg or exc.__class__.__name__)


def _generate_openai(prompt: str, system: str, key: str, json_mode: bool) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AIError("openai 패키지가 설치되지 않았습니다. (pip install openai)") from exc
    client = OpenAI(api_key=key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    kwargs = {"model": _model_for("OpenAI"), "messages": messages, "temperature": 0.2}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def _generate_gemini(prompt: str, system: str, key: str, json_mode: bool) -> str:
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise AIError(
            "google-generativeai 패키지가 설치되지 않았습니다. "
            "(pip install google-generativeai)"
        ) from exc
    genai.configure(api_key=key)
    model_name = _resolve_gemini_model(genai)
    gen_config = {"response_mime_type": "application/json"} if json_mode else None
    model = genai.GenerativeModel(
        model_name, system_instruction=system or None
    )
    resp = model.generate_content(prompt, generation_config=gen_config)
    return getattr(resp, "text", "") or ""


def _resolve_gemini_model(genai) -> str:
    """Find a Gemini model that supports generateContent for this API key.

    Honors an explicit override; otherwise tries known-good candidates against
    the account's actual model list (cached after the first success).
    """
    global _GEMINI_RESOLVED
    override = config.get("ai_model", "").strip()
    if override:
        return override
    if _GEMINI_RESOLVED:
        return _GEMINI_RESOLVED

    available: list[str] = []
    try:
        for m in genai.list_models():
            methods = getattr(m, "supported_generation_methods", []) or []
            if "generateContent" in methods:
                available.append(m.name.split("/")[-1])
    except Exception:
        available = []

    if available:
        for cand in _GEMINI_CANDIDATES:
            if cand in available:
                _GEMINI_RESOLVED = cand
                return cand
        flash = [a for a in available if "flash" in a and "vision" not in a]
        chosen = (flash or available)[0]
        _GEMINI_RESOLVED = chosen
        return chosen

    # Could not list models; fall back to the default and let the call surface
    # any error (which generate() will wrap as AIError).
    return DEFAULT_MODELS["Gemini"]


def _generate_anthropic(prompt: str, system: str, key: str) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise AIError("anthropic 패키지가 설치되지 않았습니다. (pip install anthropic)") from exc
    client = anthropic.Anthropic(api_key=key)
    resp = client.messages.create(
        model=_model_for("Anthropic"),
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
    raw = generate(prompt, system, json_mode=True)
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
        model = _model_for(provider)
        if provider == "Gemini" and not config.get("ai_model", "").strip():
            model = _GEMINI_RESOLVED or model
        return (bool(out), f"연결됨 (모델: {model})" if out else "오류: 빈 응답")
    except AIError as exc:
        return False, f"오류: {exc}"
