"""The discovery pipeline.

Implements the mermaid DAG from the plan as an explicit, readable function. The
flow has two gates, each with their own bounded re-attempt loop internal to
the subteam that runs them, plus one bounded re-iteration at the pipeline
level (closed problem via `advisor`, then - only on the first pass - an open
problem via `supervisor`):

    cafeteam (maniac -> interpreter + sceptic, re-attempts internally)
      -> GATE 1 (cafeteam's own ACCEPT/REJECT, see scoring.reattempt_decision)
           reject -> archive as FAILED transfer, stop
           accept -> advisor (closed problem)
      -> pubteam pass 1 (leangrad -> peer + critic, re-attempts internally)
      -> GATE 2 (pubteam's own ACCEPT/REJECT)
           reject -> archive as WEAK, stop
           accept -> supervisor (open problem)
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
from ..knowledge.descriptions import ensure_description
from ..knowledge.web import KnowledgeWeb
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


def _announce(name: str, verbosity: int) -> None:
    if verbosity >= 1:
        print(f"-> {name}")


def discover(web: KnowledgeWeb, seed_node: str, run: Run | None = None,
             verbosity: int = 0) -> DiscoveryResult:
    run = run or Run(seed_node=seed_node)
    res = DiscoveryResult(seed=seed_node)
    web.mark_seeded(seed_node, run.label)

    title = seed_node
    description = ensure_description(web, seed_node)

    # 1-2. cafeteam: maniac -> interpreter + sceptic, re-attempting internally
    _announce("cafeteam (maniac, interpreter, sceptic)", verbosity)
    cafe = agents.cafeteam.run_cafeteam(title, description, run=run, verbosity=verbosity)
    res.analogy = cafe.analogy
    res.novelty, res.credibility = cafe.novelty_score, cafe.credibility_score

    # GATE 1
    res.idea_passed = cafe.passed
    if not res.idea_passed:
        res.notes.append(f"Idea gate failed after {cafe.attempts} attempt(s).")
        _archive(web, res, run, verbosity=verbosity)
        return _finish(res, run)

    # 3. advisor -> closed problem
    _announce("advisor", verbosity)
    advisor_out = agents.advisor.agent({
        "maniac": cafe.analogy,
        "interpreter": cafe.novelty_text,
        "sceptic": cafe.credibility_text,
    }, run=run)
    res.closed_proposal = advisor_out.text
    grounded = list(advisor_out.meta.get("grounded", []))
    res.grounded_constants = [p.name for p in grounded]

    # 4. pubteam pass 1 (closed) - reviewers see the grounded reference values
    _announce("pubteam pass 1 (leangrad, peer, critic)", verbosity)
    pass1 = agents.pubteam.run_pubteam(
        advisor_out.text, run=run, iteration=0,
        references=data_tool.format_references(grounded))
    res.pub1_passed = pass1.passed
    if not pass1.passed:
        res.notes.append(f"Pubteam pass 1 (closed problem) failed after "
                         f"{pass1.attempts} attempt(s).")
        res.strength = classify_strength(True, False, None)
        _archive(web, res, run, problem=advisor_out.text, verbosity=verbosity)
        return _finish(res, run)

    # 5. supervisor -> open problem (only reached when iter == 0)
    _announce("supervisor", verbosity)
    supervisor_out = agents.supervisor.agent({
        "report": pass1.report,
        "peer": pass1.peer_text,
        "critic": pass1.critic_text,
    }, run=run)
    res.open_proposal = supervisor_out.text
    grounded_open = list(supervisor_out.meta.get("grounded", []))
    res.grounded_constants += [p.name for p in grounded_open]

    # 6. pubteam pass 2 (open)
    _announce("pubteam pass 2 (leangrad, peer, critic)", verbosity)
    pass2 = agents.pubteam.run_pubteam(
        supervisor_out.text, run=run, iteration=1,
        references=data_tool.format_references(grounded_open))
    res.pub2_passed = pass2.passed
    if not pass2.passed:
        res.notes.append(f"Pubteam pass 2 (open problem) failed after "
                         f"{pass2.attempts} attempt(s); closed result stands.")

    res.strength = classify_strength(True, True, pass2.passed)
    _archive(web, res, run, problem=supervisor_out.text or advisor_out.text,
            verbosity=verbosity)
    return _finish(res, run)


# --------------------------------------------------------------------------- #
# Archival (deterministic edge handling + agentic node mapping)
# --------------------------------------------------------------------------- #
def _field_from_proposal(problem: str) -> str:
    """Best-effort field label from a proposal's own opening section.

    advisor/supervisor are both prompted for a three-section proposal whose
    first section is a precise description of the phenomenon/problem - so the
    text up to the first blank line is a reasonable stand-in for "field of
    application" without a further LLM call.
    """
    return problem.strip().split("\n\n", 1)[0] or problem[:300]


def _archive(web: KnowledgeWeb, res: DiscoveryResult, run: Run,
             problem: str = "", verbosity: int = 0) -> None:
    """Insert/locate the application node and label the seed->application edge.

    Per the plan, only node-mapping is agentic; edge creation and the
    FAILED/WEAK/STRONG label are deterministic.
    """
    app_node: str | None = None
    if problem:
        _announce("archivist", verbosity)
        candidates = web.application_nodes()
        arch = agents.archivist.agent({
            "seed": res.seed,
            "field": _field_from_proposal(problem),
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
