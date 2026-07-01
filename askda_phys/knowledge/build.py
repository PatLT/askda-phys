"""Construct the initial web of knowledge from the seed pages.

Pipeline:
  1. For each seed page, fetch it and extract the concept links it points to
     (a `librarian` step that maps Wikipedia / SEP pages onto common nodes).
  2. Assemble a directed graph: page -> linked-concept, all edges STRONG.
  3. (Elsewhere) traverse once with the `memeticist` agent to set MEME/COMPLEX
     and PHILOSOPHY/APPLICATION labels and split COMPLEX nodes.

STATUS: `fetch_links` is STUBBED. Wire it to tools/reader.py (or a Wikipedia/SEP
API) to return {page_title: [linked_concept_title, ...]}. The graph assembly
below is real and works on whatever that mapping returns.
"""
from __future__ import annotations

from urllib.parse import unquote, urlparse
import re

from ..config import SEED_PAGES
from .web import KnowledgeWeb
from ..tools import reader


def _title_from_url(url: str) -> str:
    return unquote(urlparse(url).path.rsplit("/", 1)[-1]).replace("_", " ")


def fetch_links(url: str) -> list[str]:
    """STUB: return the concept titles a seed page links to.

    Replace with a real implementation (tools/reader.py + link extraction, or a
    MediaWiki API call). Returning [] keeps the builder functional but produces
    only the seed nodes themselves.
    """
    links = reader.fetch_links(url)
    wiki_links = []
    for link in links:
        parsed = urlparse(link)
        if (parsed.netloc == "en.wikipedia.org" and 
            parsed.path.startswith("/wiki/") and
            not parsed.path.startswith("/wiki/Special:") and
            not parsed.path.startswith("/wiki/Wikipedia:") and
            not parsed.path.startswith("/wiki/Talk:") and
            not parsed.path.startswith("/wiki/Help:") and
            not parsed.path.startswith("/wiki/File:") and
            not parsed.path.startswith("/wiki/Category:") and
            not parsed.path.startswith("/wiki/Template:") and
            not parsed.path.startswith("/wiki/Portal:") and
            not parsed.path.startswith("/wiki/Main_Page")):
            wiki_links.append(url)
    return wiki_links


def build_initial_web(pages: list[str] | None = None) -> KnowledgeWeb:
    pages = pages or SEED_PAGES
    web = KnowledgeWeb()
    for url in pages:
        title = _title_from_url(url)
        if title not in web.g:
            web.add_node(title, kind="COMPLEX", description="", source_url=url)
        for linked in fetch_links(url):
            if linked not in web.g:
                web.add_node(linked, kind="COMPLEX", description="")
            web.add_edge(title, linked, strength="STRONG")
    return web
