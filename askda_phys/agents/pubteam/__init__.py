"""pubteam - the publication team: leangrad (author) + peer + critic (committee).

`run_pubteam` runs leangrad's formalisation through peer (accuracy) and critic
(novelty), re-attempting up to `n_reattempts` times - with the reviewers' own
reports fed back to leangrad each time, alongside its own Lean verification
result - before settling on a final ACCEPT/REJECT via
`scoring.reattempt_decision`. The orchestrator calls it once for the
closed-problem proposal (from `advisor`) and again, if that pass is accepted
and iteration == 0, for the open-problem proposal (from `supervisor`).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ...config import N_LEANGRAD_REATTEMPTS
from ...scoring import reattempt_decision, total_score
from . import critic, leangrad, peer

if TYPE_CHECKING:
    from ...orchestration.run import Run


@dataclass
class PubResult:
    report: str
    peer_score: float | None
    critic_score: float | None
    peer_text: str
    critic_text: str
    passed: bool
    report_meta: dict
    attempts: int


def _summarise_lean(meta: dict) -> str:
    """Render leangrad's own verification attempt for peer/critic's context."""
    attempts = meta.get("lean_attempts")
    if not attempts:
        return "(no Lean verification attempted)"
    verdict = "PASSED" if meta.get("lean_verified") else "did not fully verify"
    lines = [f"{verdict} after {len(attempts)} attempt(s):"]
    lines += [f"  attempt {a['attempt']}: {a['summary']}" for a in attempts]
    return "\n".join(lines)


def _feedback_block(rounds: list[str]) -> str:
    """Concatenates all prior rounds' reviewer feedback onto leangrad's
    original proposal context; empty on the first attempt, so its prompt is
    unchanged from before this feature existed."""
    if not rounds:
        return ""
    joined = "\n\n".join(f"Round {i + 1} feedback:\n{fb}" for i, fb in enumerate(rounds))
    return f"\n\nPrevious attempt(s) were not accepted. Revise based on this feedback:\n{joined}"


def run_pubteam(proposal: str, run: "Run | None" = None,
                iteration: int = 0,
                references: str = "",
                n_reattempts: int = N_LEANGRAD_REATTEMPTS) -> PubResult:
    feedback_rounds: list[str] = []
    report = p = c = None
    for attempt in range(n_reattempts + 1):
        report = leangrad.agent(
            {"proposal": proposal, "feedback": _feedback_block(feedback_rounds)},
            run=run, iteration=iteration)
        lean_verification = _summarise_lean(report.meta)
        p = peer.agent({"report": report.text,
                        "references": references or "(none available)",
                        "lean_verification": lean_verification},
                       run=run, iteration=iteration)
        c = critic.agent({"report": report.text, "lean_verification": lean_verification},
                         run=run, iteration=iteration)

        decision = reattempt_decision(
            total_score([p.score, c.score]), attempt, n_reattempts)
        if decision != "REATTEMPT":
            return PubResult(report.text, p.score, c.score, p.text, c.text,
                             decision == "ACCEPT", report.meta, attempt + 1)
        feedback_rounds.append(
            f"Peer review (accuracy/correctness): {p.text}\n\n"
            f"Critic review (novelty): {c.text}")

    # unreachable: reattempt_decision always resolves ACCEPT/REJECT by
    # attempt == n_reattempts (see its docstring); kept as a defensive fallback.
    return PubResult(report.text, p.score, c.score, p.text, c.text,
                     False, report.meta, n_reattempts + 1)
