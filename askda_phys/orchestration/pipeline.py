"""The discovery pipeline.

Implements the mermaid DAG from the plan as an explicit, readable function. The
flow has two pass/fail gates and one bounded re-iteration (closed problem via
`advisor`, then - only on the first pass - an open problem via `supervisor`):

    maniac
      -> interpreter (novelty) + sceptic (credibility)
      -> GATE 1 (mean >= IDEA_GATE_THRESHOLD)
           fail -> archive as FAILED transfer, stop
           pass -> advisor (closed problem)
      -> pubteam pass 1 (leangrad -> peer + critic)
      -> GATE 2
           fail -> archive as WEAK, stop
           pass -> supervisor (open problem)
      -> pubteam pass 2
      -> archive (STRONG), stop

Edge-strength policy lives in `classify_strength` and is deliberately simple so
you can tune it.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .. import agents
from ..config import IDEA_GATE_THRESHOLD
from ..knowledge.web import KnowledgeWeb
from ..scoring import gate
from ..tools import data as data_tool
from .run import Run


@dataclass
class DiscoveryResult:
    seed: str
    analogy: str = ""
    novelty: float | None = None
    credibility: float | None = None
    idea_passed: bool = False
    closed_proposal: str = ""
    pub1_passed: bool | None = None
    open_proposal: str = ""
    pub2_passed: bool | None = None
    strength: str = "FAILED"          # FAILED | WEAK | STRONG
    application_node: str | None = None
    grounded_constants: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def classify_strength(idea_passed: bool, pub1_passed: bool | None,
                      pub2_passed: bool | None) -> str:
    if not idea_passed:
        return "FAILED"
    if not pub1_passed:
        return "WEAK"
    return "STRONG"  # closed-problem formalisation succeeded


def discover(web: KnowledgeWeb, seed_node: str, run: Run | None = None,
             idea_threshold: float = IDEA_GATE_THRESHOLD) -> DiscoveryResult:
    run = run or Run(seed_node=seed_node)
    res = DiscoveryResult(seed=seed_node)
    web.mark_seeded(seed_node, run.label)

    title = seed_node
    description = web.description(seed_node)

    # 1. maniac
    analogy = agents.maniac.agent(
        {"title": title, "description": description}, run=run)
    res.analogy = analogy.text

    # 2. interpreter + sceptic
    interp = agents.interpreter.agent({"maniac": analogy.text}, run=run)
    skep = agents.sceptic.agent({"maniac": analogy.text}, run=run)
    res.novelty, res.credibility = interp.score, skep.score

    # GATE 1
    res.idea_passed = gate([interp.score, skep.score], idea_threshold)
    if not res.idea_passed:
        res.notes.append("Idea gate failed.")
        _archive(web, res, run)
        return _finish(res, run)

    # 3. advisor -> closed problem
    advisor_out = agents.advisor.agent({
        "maniac": analogy.text,
        "interpreter": interp.text,
        "sceptic": skep.text,
    }, run=run)
    res.closed_proposal = advisor_out.text
    grounded = list(advisor_out.meta.get("grounded", []))
    res.grounded_constants = [p.name for p in grounded]

    # 4. pubteam pass 1 (closed) - reviewers see the grounded reference values
    pass1 = agents.pubteam.run_pubteam(
        advisor_out.text, run=run, iteration=0,
        references=data_tool.format_references(grounded))
    res.pub1_passed = pass1.passed
    if not pass1.passed:
        res.notes.append("Pubteam pass 1 (closed problem) failed.")
        res.strength = classify_strength(True, False, None)
        _archive(web, res, run, problem=advisor_out.text)
        return _finish(res, run)

    # 5. supervisor -> open problem (only reached when iter == 0)
    supervisor_out = agents.supervisor.agent({
        "report": pass1.report,
        "peer": str(pass1.peer_score),
        "critic": str(pass1.critic_score),
    }, run=run)
    res.open_proposal = supervisor_out.text
    grounded_open = list(supervisor_out.meta.get("grounded", []))
    res.grounded_constants += [p.name for p in grounded_open]

    # 6. pubteam pass 2 (open)
    pass2 = agents.pubteam.run_pubteam(
        supervisor_out.text, run=run, iteration=1,
        references=data_tool.format_references(grounded_open))
    res.pub2_passed = pass2.passed
    if not pass2.passed:
        res.notes.append("Pubteam pass 2 (open problem) failed; closed result stands.")

    res.strength = classify_strength(True, True, pass2.passed)
    _archive(web, res, run, problem=supervisor_out.text or advisor_out.text)
    return _finish(res, run)


# --------------------------------------------------------------------------- #
# Archival (deterministic edge handling + agentic node mapping)
# --------------------------------------------------------------------------- #
def _archive(web: KnowledgeWeb, res: DiscoveryResult, run: Run,
             problem: str = "") -> None:
    """Insert/locate the application node and label the seed->application edge.

    Per the plan, only node-mapping is agentic; edge creation and the
    FAILED/WEAK/STRONG label are deterministic.
    """
    app_node: str | None = None
    if problem:
        candidates = web.application_nodes()
        arch = agents.archivist.agent({
            "seed": res.seed,
            "field": "(TODO: extract field from proposal)",
            "problem": problem,
            "candidates": ", ".join(candidates) or "(none)",
        }, run=run)
        app_node = _resolve_archivist(arch.text, web, problem)

    if app_node is not None:
        res.application_node = app_node
        web.label_edge(res.seed, app_node, res.strength)


def _resolve_archivist(text: str, web: KnowledgeWeb, problem: str) -> str:
    """Parse archivist JSON; fall back to a fresh slug node on failure."""
    try:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(m.group(0)) if m else {}
    except (json.JSONDecodeError, AttributeError):
        data = {}

    if data.get("match") and data["match"] in web.g:
        return data["match"]
    if isinstance(data.get("new_node"), dict) and data["new_node"].get("title"):
        node = data["new_node"]
        if node["title"] not in web.g:
            web.add_node(node["title"], kind="MEME", role="PHENOMENON",
                         description=node.get("description", ""))
        return node["title"]

    # fallback: deterministic slug
    slug = "app:" + re.sub(r"\s+", "-", problem.strip().lower())[:48]
    if slug not in web.g:
        web.add_node(slug, kind="MEME", role="PHENOMENON", description=problem[:200])
    return slug


def _finish(res: DiscoveryResult, run: Run) -> DiscoveryResult:
    run.record("decision", {
        "seed": res.seed,
        "novelty": res.novelty,
        "credibility": res.credibility,
        "idea_passed": res.idea_passed,
        "pub1_passed": res.pub1_passed,
        "pub2_passed": res.pub2_passed,
        "strength": res.strength,
        "application_node": res.application_node,
        "grounded_constants": res.grounded_constants,
        "notes": res.notes,
    })
    return res
