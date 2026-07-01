"""Page reader tool (used by memeticist / librarian step).

Fetches a URL and returns plain-ish text. Intentionally minimal: a production
version should use a real readability/extraction library. Requires httpx; if
absent, falls back to urllib. This is the in-process "read the webpage" capability
the plan asks about - the model decides to call it, the library executes it.
"""
from __future__ import annotations

import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def fetch_html(url: str, timeout: float = 30.0) -> str:
    try:
        import httpx  # type: ignore
        r = httpx.get(url, timeout=timeout, follow_redirects=True)
        r.raise_for_status()
        return r.text
    except ImportError:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return resp.read().decode("utf-8", errors="replace")


def fetch_text(url: str, timeout: float = 30.0, max_chars: int = 20000) -> str:
    """Very naive HTML -> text. Replace with trafilatura/readability for quality."""
    html = fetch_html(url, timeout=timeout)
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html,
                  flags=re.DOTALL | re.IGNORECASE)
    text = _WS_RE.sub(" ", _TAG_RE.sub(" ", html)).strip()
    return text[:max_chars]
