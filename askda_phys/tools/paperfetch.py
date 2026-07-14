"""Fetches real papers into config.PAPERQA_PAPER_DIR so paper-qa's local
search-and-synthesize agent (tools/paperqa.py) has actual literature to
retrieve from.

paper-qa's own agent only ever searches/queries whatever is already sitting
in its local paper_directory (see tools/paperqa.py's docstring) - it never
downloads anything itself. Its bundled metadata clients (Crossref, OpenAlex,
Semantic Scholar, Unpaywall) are DOI/title lookups used to *enrich* a paper
you already have, not free-text discovery search. arXiv's public API fills
that gap: it's free, keyless, and covers this project's physics domain well.
"""
from __future__ import annotations

import re
from xml.etree import ElementTree

import httpx  # paper-qa itself hard-depends on httpx, so this is always present

from ..config import PAPERQA_PAPER_DIR, PAPERQA_PAPER_DIR_CAP

ARXIV_API = "https://export.arxiv.org/api/query"
_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_ID_RE = re.compile(r"[^A-Za-z0-9._-]")


def _evict_to_cap(cap: int) -> int:
    """Delete oldest-downloaded PDFs (by mtime, i.e. FIFO) once
    PAPERQA_PAPER_DIR holds more than `cap` files. Returns the number
    evicted. Safe to do out from under paper-qa's own ~/.pqa/indexes cache:
    its index sync (sync_with_paper_directory, on by default - see
    tools/paperqa.py's _settings) detects files missing from the directory
    and drops their index/embedding-cache entries the next time it runs."""
    files = sorted(PAPERQA_PAPER_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime)
    excess = len(files) - cap
    if excess <= 0:
        return 0
    for f in files[:excess]:
        f.unlink()
    return excess


def fetch_papers(query: str, k: int = 6, timeout: float = 30.0,
                 cap: int = PAPERQA_PAPER_DIR_CAP) -> int:
    """Search arXiv for `query` and download up to `k` PDFs into
    PAPERQA_PAPER_DIR, skipping ones already downloaded (the directory is a
    persistent, growing cache across calls/questions, not wiped per-query) -
    then evicts down to `cap` files if this pushed it over. Returns the
    number of new files saved."""
    PAPERQA_PAPER_DIR.mkdir(parents=True, exist_ok=True)
    resp = httpx.get(
        ARXIV_API,
        params={"search_query": f"all:{query}", "start": 0, "max_results": k},
        timeout=timeout,
        follow_redirects=True,
    )
    resp.raise_for_status()
    root = ElementTree.fromstring(resp.text)

    saved = 0
    for entry in root.findall(f"{_ATOM_NS}entry"):
        arxiv_id = entry.findtext(f"{_ATOM_NS}id", "")
        if not arxiv_id:
            continue
        stem = _ID_RE.sub("_", arxiv_id.rsplit("/", 1)[-1])
        dest = PAPERQA_PAPER_DIR / f"{stem}.pdf"
        if dest.exists():
            continue
        pdf_url = next(
            (link.get("href") for link in entry.findall(f"{_ATOM_NS}link")
             if link.get("title") == "pdf"),
            None,
        )
        if not pdf_url:
            continue
        pdf_resp = httpx.get(pdf_url, timeout=timeout, follow_redirects=True)
        if pdf_resp.status_code != 200 or not pdf_resp.content:
            continue
        dest.write_bytes(pdf_resp.content)
        saved += 1
    _evict_to_cap(cap)
    return saved
