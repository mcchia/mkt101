"""Centralized, secure configuration loader.

Resolution order for `ANTHROPIC_API_KEY`:
    1. Process environment (`os.environ`)
    2. Streamlit secrets (`.streamlit/secrets.toml`), when running under Streamlit
    3. `.env` in the project root (via `python-dotenv`, if installed)

The key is never printed, logged, or returned by any accessor other than
`get_api_key()`. `redact()` scrubs the key (and common API-key shapes) from
arbitrary strings before they reach logs, the UI, or error messages.
"""

from __future__ import annotations

import os
import re
from typing import Optional

_API_KEY_ENV = "ANTHROPIC_API_KEY"
_MIN_KEY_LEN = 20

_GENERIC_KEY_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}", re.IGNORECASE),
]

_cached_key: Optional[str] = None


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(override=False)


def _load_streamlit_secret() -> Optional[str]:
    try:
        import streamlit as st
    except ImportError:
        return None
    try:
        if _API_KEY_ENV in st.secrets:
            return str(st.secrets[_API_KEY_ENV])
    except Exception:
        return None
    return None


def get_api_key() -> str:
    """Return the Anthropic API key. Raises `RuntimeError` if unset/invalid.

    The error message never contains the key or any partial value.
    """
    global _cached_key
    if _cached_key:
        return _cached_key

    key = os.environ.get(_API_KEY_ENV)

    if not key:
        key = _load_streamlit_secret()

    if not key:
        _load_dotenv_if_available()
        key = os.environ.get(_API_KEY_ENV)

    if not key or len(key) < _MIN_KEY_LEN:
        raise RuntimeError(
            f"{_API_KEY_ENV} is not set. Provide it via environment variable, "
            f".env, or .streamlit/secrets.toml. See README 'Security setup'."
        )

    _cached_key = key
    return key


def has_api_key() -> bool:
    """Best-effort check without raising."""
    try:
        get_api_key()
        return True
    except RuntimeError:
        return False


def redact(text: object) -> str:
    """Return `text` with any known secret values scrubbed.

    Scrubs:
    - The currently loaded API key (exact match)
    - Common Anthropic/OpenAI-shaped keys (sk-ant-..., sk-...)
    - `Authorization: Bearer ...` tokens
    """
    s = str(text)
    if _cached_key:
        s = s.replace(_cached_key, "***REDACTED***")
    for pattern in _GENERIC_KEY_PATTERNS:
        s = pattern.sub("***REDACTED***", s)
    return s


def reset_cache() -> None:
    """Clear the cached key. Intended for tests only."""
    global _cached_key
    _cached_key = None
