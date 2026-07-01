"""Web search tool (used by advisor / supervisor / memeticist).

Uses DuckDuckGo search via the duckduckgo_search package.
"""
from __future__ import annotations

from dataclasses import dataclass
from duckduckgo_search import DDGS


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str


def web_search(query: str, k: int = 5) -> list[SearchHit]:
    """Search the web using DuckDuckGo.
    
    Args:
        query: Search query string
        k: Maximum number of results to return
        
    Returns:
        List of SearchHit objects containing title, url, and snippet
    """
    results: list[SearchHit] = []
    
    try:
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=k):
                results.append(SearchHit(
                    title=result.get("title", ""),
                    url=result.get("href", ""),
                    snippet=result.get("body", "")
                ))
    except Exception as e:
        print(f"Search failed: {e}")
    
    return results