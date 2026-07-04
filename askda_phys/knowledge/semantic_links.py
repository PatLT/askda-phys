"""Lexical SEMANTIC edges: link nodes whose ids share a rare, specific word.

Distinct from STRONG (crawl/expand-derived) and WEAK/FAILED (discovery-
pipeline outcomes): SEMANTIC edges are purely deterministic text overlap - no
model call - meant to give `ranking.rank_seeds` connectivity beyond the
STRONG-edge tree, so genuinely related nodes that memeticist happened to place
in different branches aren't treated as maximally distant.

Naive "any shared word" linking is unusable at this project's scale: on a
~2500-node web, generic domain vocabulary ('philosophy' in 161 titles,
'theory' in 90, 'physics' in 47, ...) alone generates ~28,000 edges - 10x the
entire STRONG-edge graph - swamping every other signal. Only tokens that are
*rare* across node titles (appear in at most `max_doc_freq` titles) count as a
real "shared noun"; anything more common is generic vocabulary and ignored.
"""
from __future__ import annotations

import re
from collections import defaultdict

from .web import KnowledgeWeb

_TOKEN_RE = re.compile(r"[A-Za-z']+")
_MIN_TOKEN_LEN = 4
_STOPWORDS = frozenset({
    "the", "a", "an", "of", "in", "and", "or", "to", "is", "as", "on", "for",
    "with", "by", "from", "this", "that", "its", "are", "be", "at", "not",
    "into", "your", "their", "his", "her", "who", "what", "when", "where",
})


def _tokens(title: str) -> set[str]:
    return {w.lower() for w in _TOKEN_RE.findall(title)
            if len(w) >= _MIN_TOKEN_LEN and w.lower() not in _STOPWORDS}


def add_semantic_links(web: KnowledgeWeb, *, max_doc_freq: int = 3,
                       debug: bool = False) -> int:
    """Add SEMANTIC edges (both directions) between node pairs whose ids
    share a token appearing in at most `max_doc_freq` node titles overall.

    A pair already connected by any edge (STRONG/WEAK/FAILED/SEMANTIC, either
    direction) is left alone - SEMANTIC only fills gaps, never overrides an
    existing, more meaningful relationship. Returns the number of node pairs
    newly linked.
    """
    token_to_nodes: dict[str, list[str]] = defaultdict(list)
    for title in web.g.nodes():
        for tok in _tokens(title):
            token_to_nodes[tok].append(title)

    added = 0
    seen_pairs: set[tuple[str, str]] = set()
    for tok, nodes in token_to_nodes.items():
        if not (2 <= len(nodes) <= max_doc_freq):
            continue
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                a, b = sorted((nodes[i], nodes[j]))
                if (a, b) in seen_pairs:
                    continue
                seen_pairs.add((a, b))
                if web.g.has_edge(a, b) or web.g.has_edge(b, a):
                    continue
                web.add_edge(a, b, strength="SEMANTIC")
                web.add_edge(b, a, strength="SEMANTIC")
                added += 1
                if debug:
                    print(f"SEMANTIC: {a!r} <-> {b!r}  (shared token: {tok!r})")
    return added
