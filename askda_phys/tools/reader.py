"""Page reader tool (used by memeticist / librarian step).

Fetches a URL and returns plain-ish text. Intentionally minimal: a production
version should use a real readability/extraction library. Requires httpx; if
absent, falls back to urllib. This is the in-process "read the webpage" capability
the plan asks about - the model decides to call it, the library executes it.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin,urlparse

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

def fetch_links(url: str, timeout: float = 30.0, max_links: int = 100) -> list[str]:
    """Extract outbound links from a webpage.
    
    Fetches the URL and extracts all href attributes from <a> tags.
    Relative URLs are resolved to absolute URLs.
    
    Args:
        url: The webpage URL to fetch
        timeout: Request timeout in seconds
        max_links: Maximum number of links to return
        
    Returns:
        List of absolute URLs found on the page
    """
    html = fetch_html(url, timeout=timeout)
    
    # Extract all href attributes from <a> tags
    # This pattern handles common variations: href="...", href='...', href=... (no quotes)
    href_pattern = re.compile(
        r'<a\s[^>]*href\s*=\s*["\']?([^"\'\s>]+)["\']?[^>]*>',
        re.IGNORECASE
    )
    
    links = []
    seen = set()  # deduplicate while preserving order
    
    for match in href_pattern.finditer(html):
        raw_href = match.group(1).strip()
        
        # Skip empty links, javascript:, mailto:, tel:, etc.
        if not raw_href or raw_href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            continue
        
        # Resolve relative URLs to absolute
        absolute_url = urljoin(url, raw_href)
        
        # Only include http(s) URLs and deduplicate
        parsed = urlparse(absolute_url)
        if parsed.scheme in ('http', 'https') and absolute_url not in seen:
            seen.add(absolute_url)
            links.append(absolute_url)
            
            if len(links) >= max_links:
                break
    
    return links