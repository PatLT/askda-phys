"""The web of knowledge.

A directed graph of concepts in physics, philosophy and related fields.

Node attributes
---------------
kind        : "MEME" | "COMPLEX"        (set by memeticist; COMPLEX until split)
role        : see `agents.memeticist.ALL_ROLES` for the full set and their
              meaning, or None if not yet classified. Only PHILOSOPHY_CONCEPT
              is usable as a seed for `maniac`; PHILOSOPHY_SCHOOL and
              PHILOSOPHER are not seeds themselves but are decomposed
              (`agents.memeticist.EXPANDABLE_ROLES`) into concepts that are.
              PHENOMENON marks an application target; SCIENCE_CONCEPT,
              SCIENTIST, and OTHER are terminal - never expanded, never seeds.
description : short text (the seed prompt for `maniac`, for MEME nodes)
seeded_runs : list[str]                  run labels that have used this as a seed

Edge attributes
---------------
strength    : "STRONG" | "WEAK" | "FAILED"
"""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

NodeKind = str       # "MEME" | "COMPLEX"
NodeRole = str       # see agents.memeticist.ALL_ROLES
EdgeStrength = str   # "STRONG" | "WEAK" | "FAILED"


class KnowledgeWeb:
    def __init__(self, graph: nx.DiGraph | None = None):
        self.g: nx.DiGraph = graph if graph is not None else nx.DiGraph()

    # -- mutation ----------------------------------------------------------- #
    def add_node(self, node_id: str, *, kind: NodeKind = "COMPLEX",
                 role: NodeRole | None = None, description: str = "",
                 **attrs) -> None:
        self.g.add_node(node_id, kind=kind, role=role, description=description,
                        seeded_runs=[], **attrs)

    def add_edge(self, src: str, dst: str, *, strength: EdgeStrength = "STRONG",
                 **attrs) -> None:
        self.g.add_edge(src, dst, strength=strength, **attrs)

    def set_kind(self, node_id: str, kind: NodeKind) -> None:
        self.g.nodes[node_id]["kind"] = kind

    def set_role(self, node_id: str, role: NodeRole) -> None:
        self.g.nodes[node_id]["role"] = role

    def mark_seeded(self, node_id: str, run_label: str) -> None:
        self.g.nodes[node_id].setdefault("seeded_runs", []).append(run_label)

    def label_edge(self, src: str, dst: str, strength: EdgeStrength) -> None:
        if not self.g.has_edge(src, dst):
            self.add_edge(src, dst, strength=strength)
        else:
            self.g.edges[src, dst]["strength"] = strength

    # -- queries ------------------------------------------------------------ #
    def meme_nodes(self) -> list[str]:
        return [n for n, d in self.g.nodes(data=True) if d.get("kind") == "MEME"]

    def application_nodes(self) -> list[str]:
        return [n for n, d in self.g.nodes(data=True)
                if d.get("role") == "PHENOMENON"]

    def unused_seed_nodes(self) -> list[str]:
        return [
            n for n, d in self.g.nodes(data=True)
            if d.get("kind") == "MEME"
            and d.get("role") == "PHILOSOPHY_CONCEPT"
            and not d.get("seeded_runs")
        ]

    def description(self, node_id: str) -> str:
        return self.g.nodes[node_id].get("description", "")

    def strong_subgraph(self) -> nx.DiGraph:
        keep = [(u, v) for u, v, d in self.g.edges(data=True)
                if d.get("strength") == "STRONG"]
        return self.g.edge_subgraph(keep).copy()

    # -- persistence -------------------------------------------------------- #
    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self.g, edges="links")
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "KnowledgeWeb":
        data = json.loads(Path(path).read_text())
        return cls(nx.node_link_graph(data, directed=True, edges="links"))

    def __len__(self) -> int:
        return self.g.number_of_nodes()
