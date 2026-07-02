"""Run the `memeticist` agent over the web of knowledge.

Per the plan: visit each COMPLEX node, ask memeticist whether it is a single
memetic unit (MEME) or should be split, apply the returned kind/role to the
node, and - for a COMPLEX split - add each returned child as a new MEME node
linked back to the parent with a STRONG edge. Children are taken as final (the
plan: "This label does not need to be inherited...") so they are not
re-visited in the same pass.
"""
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from .. import agents
from .web import KnowledgeWeb

if TYPE_CHECKING:  # avoid a hard import cycle with orchestration
    from ..orchestration.run import Run

_ROLES = {"CONCEPT", "PHENOMENON", "OTHER"}


def _parse_response(text: str) -> dict:
    """Parse memeticist's JSON reply; fall back to a safe MEME/no-op on failure."""
    try:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(m.group(0)) if m else {}
    except (json.JSONDecodeError, AttributeError):
        data = {}

    kind = data.get("kind") if data.get("kind") in ("MEME", "COMPLEX") else "MEME"
    role = data.get("role") if data.get("role") in _ROLES else None
    children = data.get("children") if isinstance(data.get("children"), list) else []
    return {"kind": kind, "role": role, "children": children}


def _apply(web: KnowledgeWeb, node: str, parsed: dict) -> None:
    web.set_kind(node, parsed["kind"])
    if parsed["role"] is not None:
        web.set_role(node, parsed["role"])

    for child in parsed["children"]:
        if not isinstance(child, dict):
            continue
        title = child.get("title")
        if not title:
            continue
        if title not in web.g:
            web.add_node(title, kind="MEME", description=child.get("description", ""))
        role = child.get("role")
        if role in _ROLES:
            web.set_role(title, role)
        if title != node:
            web.add_edge(node, title, strength="STRONG")


def trawl_web(web: KnowledgeWeb, run: "Run | None" = None, *,
              nodes: list[str] | None = None, debug: bool = False) -> int:
    """Run one memeticist pass over `web`, mutating it in place.

    By default visits every node still labelled COMPLEX (the state every node
    starts in after `build_initial_web`); pass `nodes` to target a specific
    subset instead. Returns the number of nodes visited.
    """
    targets = nodes if nodes is not None else [
        n for n, d in web.g.nodes(data=True) if d.get("kind") == "COMPLEX"
    ]
    for node in targets:
        if node not in web.g:
            continue
        result = agents.memeticist.agent(
            {"title": node, "description": web.description(node)}, run=run)
        parsed = _parse_response(result.text)
        if debug:
            print(f"{node}: kind={parsed['kind']} role={parsed['role']} "
                  f"children={len(parsed['children'])}")
        _apply(web, node, parsed)
    return len(targets)
