"""Run the `memeticist` agent over the web of knowledge.

Two phases, so the expensive decomposition call is only ever paid for nodes
that can actually source a seed:

  1. classify - cheap, no tools. Every node with role=None gets exactly one
     of `agents.memeticist.ALL_ROLES`.
  2. expand - the heavier, tool-using call. Only nodes whose role is in
     `agents.memeticist.EXPANDABLE_ROLES` (PHILOSOPHY_CONCEPT,
     PHILOSOPHY_SCHOOL, PHILOSOPHER) and that are still COMPLEX get
     decomposed into MEME children, each linked back to the parent with a
     STRONG edge. Children are taken as final (the plan: "This label does
     not need to be inherited...") so they are not re-visited in the same
     pass.
"""
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Callable

from tqdm import tqdm

from .. import agents
from ..agents.memeticist import ALL_ROLES, EXPANDABLE_ROLES
from .web import KnowledgeWeb

if TYPE_CHECKING:  # avoid a hard import cycle with orchestration
    from ..orchestration.run import Run


def _extract_json(text: str) -> dict:
    try:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(m.group(0)) if m else {}
    except (json.JSONDecodeError, AttributeError):
        return {}


def _parse_role(text: str) -> str | None:
    """Parse classify's JSON reply; None (unclassified, retried next pass) on failure."""
    role = _extract_json(text).get("role")
    return role if role in ALL_ROLES else None


def _parse_expand(text: str) -> dict:
    """Parse expand's JSON reply; fall back to a safe MEME/no-op on failure."""
    data = _extract_json(text)
    kind = data.get("kind") if data.get("kind") in ("MEME", "COMPLEX") else "MEME"
    children = data.get("children") if isinstance(data.get("children"), list) else []
    return {"kind": kind, "children": children}


def _apply_expand(web: KnowledgeWeb, node: str, parsed: dict) -> None:
    web.set_kind(node, parsed["kind"])
    for child in parsed["children"]:
        if not isinstance(child, dict):
            continue
        title = child.get("title")
        if not title:
            continue
        if title not in web.g:
            web.add_node(title, kind="MEME", description=child.get("description", ""))
        role = child.get("role")
        if role in ALL_ROLES:
            web.set_role(title, role)
        if title != node:
            web.add_edge(node, title, strength="STRONG")


def _classify_pass(web: KnowledgeWeb, run: "Run | None", targets: list[str],
                   verbosity: int, checkpoint: Callable[[], None] | None) -> None:
    for node in tqdm(targets, desc="label-web classify", unit="node",
                     disable=verbosity < 1):
        if node not in web.g:
            continue
        result = agents.memeticist.classify_agent(
            {"title": node, "description": web.description(node)}, run=run)
        role = _parse_role(result.text)
        if verbosity >= 2:
            tqdm.write(f"{node}: role={role}")
        if role is not None:
            web.set_role(node, role)
        if checkpoint is not None:
            checkpoint()


def _expand_pass(web: KnowledgeWeb, run: "Run | None", targets: list[str],
                 verbosity: int, checkpoint: Callable[[], None] | None) -> None:
    for node in tqdm(targets, desc="label-web expand", unit="node",
                     disable=verbosity < 1):
        if node not in web.g:
            continue
        result = agents.memeticist.expand_agent(
            {"title": node, "description": web.description(node)}, run=run)
        parsed = _parse_expand(result.text)
        if verbosity >= 2:
            tqdm.write(f"{node}: kind={parsed['kind']} "
                      f"children={len(parsed['children'])}")
        _apply_expand(web, node, parsed)
        if checkpoint is not None:
            checkpoint()


def trawl_web(web: KnowledgeWeb, run: "Run | None" = None, *,
              nodes: list[str] | None = None, verbosity: int = 0,
              checkpoint: Callable[[], None] | None = None) -> int:
    """Run one classify+expand memeticist pass over `web`, mutating it in place.

    By default classifies every node with role=None; pass `nodes` to target a
    specific subset instead. Expansion always targets whatever is left in an
    EXPANDABLE_ROLES + COMPLEX state after classification (including nodes
    that were already in that state before this call). Returns the total
    number of agent calls made (classify + expand).

    verbosity: 0 = silent, 1 = progress bars, 2 = progress bars + per-node
    debug prints.

    `checkpoint`, if given, is called after every node in both phases - e.g.
    to persist the web to disk incrementally so a crash mid-pass doesn't lose
    already-decided labels.
    """
    to_classify = nodes if nodes is not None else [
        n for n, d in web.g.nodes(data=True) if d.get("role") is None
    ]
    _classify_pass(web, run, to_classify, verbosity, checkpoint)

    to_expand = [
        n for n, d in web.g.nodes(data=True)
        if d.get("role") in EXPANDABLE_ROLES and d.get("kind") == "COMPLEX"
    ]
    _expand_pass(web, run, to_expand, verbosity, checkpoint)

    return len(to_classify) + len(to_expand)
