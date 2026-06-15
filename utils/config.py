"""Configuration and API-key resolution for IP3.

Resolution order for any key:
    1. Value saved in the in-app Settings screen (settings table)
    2. Environment variable (.env / OS environment)
    3. Provided default
"""
from __future__ import annotations

import os
from pathlib import Path

from utils import db

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env once, if python-dotenv is available.
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except Exception:  # pragma: no cover - optional dependency
    pass


# Mapping of logical setting keys -> environment variable names.
ENV_FALLBACK = {
    "kiprisplus_api_key": "KIPRISPLUS_API_KEY",
    "ai_api_key": "AI_API_KEY",
    "ai_provider": "AI_PROVIDER",
}

DEFAULTS = {
    "search_scope": "국내+해외",
    "top_n": "20",
    "default_sort": "유사도순",
    "ai_provider": "사용 안 함",
    "cache_enabled": "1",
    "report_dir": str(BASE_DIR / "data" / "exports"),
    "ai_fields": "유사한 점,차이점,확인할 점,확인 위치,원문 근거,판단 상태",
}

AI_PROVIDERS = ["Gemini", "OpenAI", "Anthropic", "Local/Other", "사용 안 함"]
SEARCH_SCOPES = ["국내", "해외", "국내+해외"]
TOP_N_OPTIONS = [10, 20, 50]
SORT_OPTIONS = ["유사도순", "최신순"]


def get(key: str, default: str | None = None) -> str:
    """Resolve a configuration value with the documented precedence."""
    value = db.get_setting(key, "")
    if value:
        return value
    env_name = ENV_FALLBACK.get(key)
    if env_name:
        env_value = os.environ.get(env_name, "")
        if env_value:
            return env_value
    if default is not None:
        return default
    return DEFAULTS.get(key, "")


def set(key: str, value: str) -> None:
    db.set_setting(key, value)


def get_kiprisplus_key() -> str:
    return get("kiprisplus_api_key", "")


def get_ai_provider() -> str:
    return get("ai_provider", DEFAULTS["ai_provider"])


def get_ai_key() -> str:
    return get("ai_api_key", "")


def get_report_dir() -> Path:
    p = Path(get("report_dir", DEFAULTS["report_dir"]))
    p.mkdir(parents=True, exist_ok=True)
    return p


def has_kiprisplus() -> bool:
    return bool(get_kiprisplus_key().strip())


def has_ai() -> bool:
    return get_ai_provider() not in ("", "사용 안 함") and bool(get_ai_key().strip())


def get_default_top_n() -> int:
    try:
        return int(get("top_n", DEFAULTS["top_n"]))
    except (ValueError, TypeError):
        return 20
