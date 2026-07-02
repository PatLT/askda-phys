"""Construct the initial web of knowledge from the seed pages.

Pipeline:
  1. For each seed page, fetch it and extract the concept links it points to
     (a `librarian` step that maps Wikipedia / SEP pages onto common nodes).
  2. Assemble a directed graph: page -> linked-concept, all edges STRONG.
  3. (Elsewhere) traverse once with the `memeticist` agent to set MEME/COMPLEX
     and role labels (see `agents.memeticist.ALL_ROLES`) and split COMPLEX
     nodes.

STATUS: `fetch_links` is STUBBED. Wire it to tools/reader.py (or a Wikipedia/SEP
API) to return {page_title: [linked_concept_title, ...]}. The graph assembly
below is real and works on whatever that mapping returns.
"""
from __future__ import annotations

from urllib.parse import unquote, urlparse

from tqdm import tqdm

from ..config import SEED_PAGES
from .web import KnowledgeWeb
from ..tools import reader


def _title_from_url(url: str) -> str:
    return unquote(urlparse(url).path.rsplit("/", 1)[-1]).replace("_", " ")


def fetch_links(url: str) -> list[str]:
    """Return the concept titles a seed page links to.

    Currently scrapes wiki page for appropriate links. 
    Might want to upgrade this to a MediaWiki API call. 
    """
    links = reader.fetch_urls(url,max_links=3000)
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
            wiki_links.append(link)
    return wiki_links


def build_initial_web(pages: list[str] | None = None, max_depth: int = 2,
                      verbosity: int = 0) -> KnowledgeWeb:
    """verbosity: 0 = silent, 1 = progress bar over links processed,
    2 = progress bar + per-link debug prints."""
    pages = pages or SEED_PAGES
    web = KnowledgeWeb()
    # Total grows as new links are discovered, so the bar tracks "processed so
    # far / known so far" rather than a true upfront percentage.
    pbar = tqdm(total=len(pages), desc="build-web", unit="link",
               disable=verbosity < 1)
    def _recurse(links: list[str], parent: None | str, depth: int):
        if depth == max_depth:
            return
        if verbosity >= 2: tqdm.write(f'DEPTH = {depth}, {len(links)} links')
        for link in links:
            title = _title_from_url(link)
            if verbosity >= 2: tqdm.write(f'\t{parent} -> {title} | {link}')
            if title not in web.g:
                web.add_node(title, kind="COMPLEX", description="", source_url=link)
                if parent is not None and parent!=title:
                    web.add_edge(parent,title,strength="STRONG")
                if depth+1<max_depth:
                    # Fetching links takes time so only do it if it's needed at the next step.
                    new_links = fetch_links(link)
                    if new_links:
                        pbar.total += len(new_links)
                        pbar.refresh()
                else:
                    new_links = []
                _recurse(new_links,title,depth+1)
            pbar.update(1)
    _recurse(pages,None,0)
    pbar.close()
    return web
