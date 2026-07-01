"""Rank memetic starting points in the web of knowledge.

Per the plan: take the STRONG-edge subgraph, compute centrality of each node,
score each (unused) seed node by

    score = distance_to_nearest_application_node
            - centrality_of_nearest_application_node

and return the highest-scored, as-yet-unused seed node. Intuition: favour seeds
that sit far from where the framework has already been applied, but whose nearest
application is not a heavily-trafficked hub - i.e. genuinely unexplored frontier.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from .web import KnowledgeWeb


@dataclass
class SeedScore:
    node: str
    score: float
    nearest_application: str | None
    distance: float
    nearest_centrality: float


def _centrality(graph: nx.DiGraph, kind: str = "betweenness") -> dict[str, float]:
    if graph.number_of_nodes() == 0:
        return {}
    if kind == "degree":
        return nx.degree_centrality(graph)
    return nx.betweenness_centrality(graph)


def rank_seeds(web: KnowledgeWeb, *, centrality: str = "betweenness",
               include_unreachable: bool = False) -> list[SeedScore]:
    sub = web.strong_subgraph()
    und = sub.to_undirected()
    cent = _centrality(sub, centrality)
    apps = set(web.application_nodes()) & set(sub.nodes())

    scored: list[SeedScore] = []
    for seed in web.unused_seed_nodes():
        if seed not in und:
            continue
        nearest, dist = _nearest_application(und, seed, apps)
        if nearest is None and not include_unreachable:
            continue
        d = dist if nearest is not None else float("inf")
        c = cent.get(nearest, 0.0) if nearest is not None else 0.0
        scored.append(SeedScore(seed, d - c, nearest, d, c))

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


def _nearest_application(graph: nx.Graph, seed: str,
                         apps: set[str]) -> tuple[str | None, float]:
    if not apps:
        return None, float("inf")
    lengths = nx.single_source_shortest_path_length(graph, seed)
    reachable = [(a, lengths[a]) for a in apps if a in lengths]
    if not reachable:
        return None, float("inf")
    node, dist = min(reachable, key=lambda kv: kv[1])
    return node, float(dist)


def best_seed(web: KnowledgeWeb, **kwargs) -> str | None:
    ranked = rank_seeds(web, **kwargs)
    return ranked[0].node if ranked else None
