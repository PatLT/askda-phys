"""Run the `memeticist` agent over the web of knowledge.

Two phases, so the expensive decomposition call is only ever paid for nodes
that can actually source a seed:

  1. classify - cheap, no tools. Every node with role=None gets exactly one
     of `agents.memeticist.ALL_ROLES`.
  2. expand - the heavier, tool-using call. Only nodes whose role is in
     `expandable_roles` (`trawl_web`'s parameter, default
     `agents.memeticist.EXPANDABLE_ROLES` = PHILOSOPHY_CONCEPT,
     PHILOSOPHY_SCHOOL, PHILOSOPHER) and that are still COMPLEX get
     decomposed into MEME children, each linked back to the parent with a
     STRONG edge. Children are taken as final (the plan: "This label does
     not need to be inherited...") so they are not re-visited in the same
     pass. Before inserting a child, `_find_existing` checks it against nodes
     already in the web via exact-then-fuzzy title matching (see
     `_canonical`/`_is_negation_pair`) - deterministic, no extra model call -
     and reuses the existing node instead of creating a near-duplicate.
"""
from __future__ import annotations

import difflib
import json
import re
from collections import Counter
from typing import TYPE_CHECKING, Callable

from tqdm import tqdm

from .. import agents
from ..agents.memeticist import ALL_ROLES, EXPANDABLE_ROLES
from .web import KnowledgeWeb

if TYPE_CHECKING:  # avoid a hard import cycle with orchestration
    from ..orchestration.run import Run

# Duplicate-title matching for expand's new children - deterministic, no LLM
# call. Conservative on purpose: a missed duplicate just costs a redundant
# node, but a false merge silently conflates two distinct concepts.
_FUZZY_CUTOFF = 0.92
_NEGATION_PREFIXES = ("non", "un", "in", "im", "dis", "a")

_PAREN_RE = re.compile(r"\s*\([^)]*\)")
_PUNCT_RE = re.compile(r"[^\w\s]")
_WS_RE = re.compile(r"\s+")


def _canonical(title: str) -> str:
    """Normalize for matching: drop parentheticals/punctuation, collapse
    whitespace, lowercase. Deliberately not stemmed - stays conservative."""
    t = _PAREN_RE.sub("", title)
    t = _PUNCT_RE.sub(" ", t)
    return _WS_RE.sub(" ", t).strip().lower()


def _is_negation_pair(a: str, b: str) -> bool:
    """True if one canonical title is the other plus a leading negation
    morpheme (e.g. 'determinism'/'indeterminism', 'self'/'non self') - near-
    identical strings, opposite concepts. Fuzzy matching must never merge
    these regardless of similarity score."""
    shorter, longer = sorted((a, b), key=len)
    if not shorter or not longer.endswith(shorter):
        return False
    return longer[: len(longer) - len(shorter)].strip() in _NEGATION_PREFIXES


def _find_existing(web: KnowledgeWeb, title: str) -> str | None:
    """Find a node `title` most likely duplicates, via exact-then-fuzzy string
    matching only (no model call). None if nothing looks like a real dup."""
    if title in web.g:
        return title
    canonical = _canonical(title)
    best_id, best_ratio = None, 0.0
    for other in web.g.nodes:
        other_canonical = _canonical(other)
        if other_canonical == canonical:
            return other
        if _is_negation_pair(canonical, other_canonical):
            continue
        ratio = difflib.SequenceMatcher(None, canonical, other_canonical).ratio()
        if ratio > best_ratio:
            best_id, best_ratio = other, ratio
    return best_id if best_ratio >= _FUZZY_CUTOFF else None


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
        existing = _find_existing(web, title)
        if existing is None:
            web.add_node(title, kind="MEME", description=child.get("description", ""))
            existing = title
        role = child.get("role")
        # first-write-wins, matching description's semantics: don't clobber a
        # role a duplicate node was already given by an earlier expand call.
        if role in ALL_ROLES and web.g.nodes[existing].get("role") is None:
            web.set_role(existing, role)
        if existing != node:
            web.add_edge(node, existing, strength="STRONG")


def _classify_pass(web: KnowledgeWeb, run: "Run | None", targets: list[str],
                   verbosity: int, checkpoint: Callable[[], None] | None) -> None:
    counts: Counter[str] = Counter()
    for node in tqdm(targets, desc="label-web classify", unit="node",
                     disable=verbosity < 1):
        if node not in web.g:
            continue
        result = agents.memeticist.classify_agent(
            {"title": node, "description": web.description(node)}, run=run)
        role = _parse_role(result.text)
        if verbosity >= 2:
            tqdm.write(f"{node}: role={role}")
        counts[role or "UNCLASSIFIED"] += 1
        if role is not None:
            web.set_role(node, role)
        if checkpoint is not None:
            checkpoint()
    if verbosity >= 1 and targets:
        summary = ", ".join(f"{role}={n}"
                            for role, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
        print(f"classify: {summary}")


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
              checkpoint: Callable[[], None] | None = None,
              expandable_roles: frozenset[str] | None = None) -> int:
    """Run one classify+expand memeticist pass over `web`, mutating it in place.

    By default classifies every node with role=None; pass `nodes` to target a
    specific subset instead. Expansion targets whatever is left in an
    `expandable_roles` + COMPLEX state after classification (including nodes
    that were already in that state before this call). `expandable_roles`
    defaults to `agents.memeticist.EXPANDABLE_ROLES`; pass a narrower (or
    wider - any subset of `ALL_ROLES`) set to restrict which roles the
    (expensive) expand call is spent on. Returns the total number of agent
    calls made (classify + expand).

    verbosity: 0 = silent, 1 = progress bars, 2 = progress bars + per-node
    debug prints.

    `checkpoint`, if given, is called after every node in both phases - e.g.
    to persist the web to disk incrementally so a crash mid-pass doesn't lose
    already-decided labels.
    """
    roles = expandable_roles if expandable_roles is not None else EXPANDABLE_ROLES
    invalid = roles - ALL_ROLES
    if invalid:
        raise ValueError(f"not a valid role: {', '.join(sorted(invalid))}; "
                         f"expected a subset of {sorted(ALL_ROLES)}")

    to_classify = nodes if nodes is not None else [
        n for n, d in web.g.nodes(data=True) if d.get("role") is None
    ]
    _classify_pass(web, run, to_classify, verbosity, checkpoint)

    to_expand = [
        n for n, d in web.g.nodes(data=True)
        if d.get("role") in roles and d.get("kind") == "COMPLEX"
    ]
    _expand_pass(web, run, to_expand, verbosity, checkpoint)

    return len(to_classify) + len(to_expand)
