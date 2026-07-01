"""Web search tool (used by advisor / supervisor / memeticist).

STATUS: STUBBED. Wire to a search API (SerpAPI, Tavily, Brave, a self-hosted
SearXNG, etc.). Ollama cannot search the web itself - this runs in-process and
its results are fed back into the agent's next prompt.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str


def web_search(query: str, k: int = 5) -> list[SearchHit]:
    raise NotImplementedError(
        "tools.search.web_search is a stub; wire it to a search backend."
    )
