"""Backfill blank node descriptions from their source wiki page.

Nodes created directly by `build.build_initial_web`'s crawl start with
description="" (only `source_url` is known at crawl time); nodes created by
`memeticist`'s expand step get a real description from the model. That left a
real gap: any un-expanded, crawl-only seed handed to `maniac` (via
`context_template`'s {title}/{description}) carried essentially no
descriptive context beyond its bare title.

`ensure_description` fixes this lazily, at the point a seed is actually used
(not for the whole graph up front, which would mean fetching thousands of
pages nobody ends up seeding with) - deterministic, no model call: pull the
first substantial paragraph off `source_url`
(`tools.reader.fetch_first_paragraph`) and persist it onto the node so it's
only ever fetched once.
"""
from __future__ import annotations

from ..tools import reader
from .web import KnowledgeWeb


def ensure_description(web: KnowledgeWeb, node_id: str) -> str:
    """Return `node_id`'s description, backfilling and persisting it from its
    `source_url` (a plain paragraph fetch, no model call) if currently blank.

    A no-op (returns "") if the description is blank and there's no
    `source_url` to backfill from (e.g. a MEME child memeticist decomposed
    without a source page of its own).
    """
    existing = web.description(node_id)
    if existing:
        return existing
    source_url = web.g.nodes[node_id].get("source_url")
    if not source_url:
        return ""
    text = reader.fetch_first_paragraph(source_url)
    if text:
        web.g.nodes[node_id]["description"] = text
    return text
