"""Rank memetic starting points in the web of knowledge.

Score each (unused) PHILOSOPHY_CONCEPT seed node by

    score = distance(seed, nearest PHENOMENON)
            - CENTRALITY_SCALE * centrality(nearest PHENOMENON)
            - CENTRALITY_SCALE * centrality(nearest SCIENCE_CONCEPT)

and return the highest-scored, as-yet-unused seed node (ties broken randomly,
not by node-iteration order - see `rank_seeds`' shuffle). Intuition: favour
seeds that sit far from where the framework has already been applied
(distance), but discount seeds whose nearest landing spot is already
well-referenced (phenomenon centrality) or that sit near an already
heavily-cited theoretical concept (science centrality) - i.e. genuinely
unexplored frontier, not just raw distance.

Centrality here is in-degree centrality, not betweenness. PHENOMENON /
SCIENCE_CONCEPT (and SCIENTIST / OTHER) are never expanded by memeticist (see
`agents.memeticist.EXPANDABLE_ROLES`), so they never gain outgoing edges -
which makes their *directed* betweenness centrality mathematically zero no
matter how many places reference them (a sink can never lie "between" two
other nodes on a directed shortest path). In-degree centrality - how many
parents already point here - is what actually varies and carries signal for
these roles; betweenness/degree remain available via `centrality=...` for
comparison, but in-degree is the sensible default.

CENTRALITY_SCALE exists because networkx normalizes in-degree centrality by
1/(n-1): on a graph of a few thousand nodes each additional parent only adds
~1/n to a node's centrality, dwarfed by a single hop of `distance`. The scale
factor brings it back onto a comparable footing; `SeedScore`'s
`phenomenon_centrality`/`science_centrality` fields stay unscaled (the raw
networkx value) for diagnostic purposes - only `score` applies the factor.

Distance and centrality are both computed over STRONG + SEMANTIC edges (see
`knowledge/semantic_links.py`), not STRONG alone - so two nodes memeticist
never directly connected, but whose ids share a rare/specific word, are no
longer treated as maximally distant from each other.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

import networkx as nx

from .web import KnowledgeWeb

CENTRALITY_SCALE = 1000


@dataclass
class SeedScore:
    node: str
    score: float
    nearest_phenomenon: str | None
    distance: float
    phenomenon_centrality: float
    nearest_science: str | None
    science_centrality: float


def _centrality(graph: nx.DiGraph, kind: str = "in_degree") -> dict[str, float]:
    if graph.number_of_nodes() == 0:
        return {}
    if kind == "degree":
        return nx.degree_centrality(graph)
    if kind == "betweenness":
        return nx.betweenness_centrality(graph)
    return nx.in_degree_centrality(graph)


def rank_seeds(web: KnowledgeWeb, *, centrality: str = "in_degree",
               include_unreachable: bool = False,
               rng: random.Random | None = None) -> list[SeedScore]:
    sub = web.edge_subgraph_by_strength({"STRONG", "SEMANTIC"})
    und = sub.to_undirected()
    cent = _centrality(sub, centrality)
    phenomena = set(web.application_nodes()) & set(sub.nodes())
    science = ({n for n, d in web.g.nodes(data=True) if d.get("role") == "SCIENCE_CONCEPT"}
              & set(sub.nodes()))

    # list.sort() is stable, so shuffling before scoring randomizes which
    # node wins among ties (e.g. same-distance seeds) instead of always
    # resolving them in whatever order the graph happens to iterate in.
    seeds = list(web.unused_seed_nodes())
    (rng or random).shuffle(seeds)

    scored: list[SeedScore] = []
    for seed in seeds:
        if seed not in und:
            continue
        nearest_phen, dist = _nearest_in_set(und, seed, phenomena, cent)
        if nearest_phen is None and not include_unreachable:
            continue
        d = dist if nearest_phen is not None else float("inf")
        c_phen = cent.get(nearest_phen, 0.0) if nearest_phen is not None else 0.0

        nearest_sci, _ = _nearest_in_set(und, seed, science, cent)
        c_sci = cent.get(nearest_sci, 0.0) if nearest_sci is not None else 0.0

        score = d - CENTRALITY_SCALE * c_phen - CENTRALITY_SCALE * c_sci
        scored.append(SeedScore(seed, score, nearest_phen, d, c_phen, nearest_sci, c_sci))

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


def _nearest_in_set(graph: nx.Graph, seed: str, targets: set[str],
                    cent: dict[str, float]) -> tuple[str | None, float]:
    if not targets:
        return None, float("inf")
    lengths = nx.single_source_shortest_path_length(graph, seed)
    reachable = [(t, lengths[t]) for t in targets if t in lengths]
    if not reachable:
        return None, float("inf")
    # Deterministic tie-break - NOT set/hash iteration order, which Python
    # randomizes per process (PYTHONHASHSEED), so the same graph could
    # otherwise report a different "nearest" node (and therefore a different
    # score) across separate `rank` invocations with nothing actually
    # changed. Among nodes tied for nearest, prefer the more-central one
    # (conservative: even the closest landing spot might already be a hub);
    # node id as a final tiebreak in case centrality also ties.
    node, dist = min(reachable, key=lambda kv: (kv[1], -cent.get(kv[0], 0.0), kv[0]))
    return node, float(dist)


def best_seed(web: KnowledgeWeb, **kwargs) -> str | None:
    ranked = rank_seeds(web, **kwargs)
    return ranked[0].node if ranked else None
