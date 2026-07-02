"""pubteam - the publication team: leangrad (author) + peer + critic (committee).

`run_pubteam` executes one formalisation-and-review pass and returns the report,
the two reviewer scores, and the gate decision. The orchestrator calls it once
for the closed-problem proposal (from `advisor`) and again, if the first pass
passes and iteration == 0, for the open-problem proposal (from `supervisor`).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ...config import PUB_GATE_THRESHOLD
from ...scoring import gate
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


def _summarise_lean(meta: dict) -> str:
    """Render leangrad's own verification attempt for peer/critic's context."""
    attempts = meta.get("lean_attempts")
    if not attempts:
        return "(no Lean verification attempted)"
    verdict = "PASSED" if meta.get("lean_verified") else "did not fully verify"
    lines = [f"{verdict} after {len(attempts)} attempt(s):"]
    lines += [f"  attempt {a['attempt']}: {a['summary']}" for a in attempts]
    return "\n".join(lines)


def run_pubteam(proposal: str, run: "Run | None" = None,
                iteration: int = 0,
                threshold: float = PUB_GATE_THRESHOLD,
                references: str = "") -> PubResult:
    report = leangrad.agent({"proposal": proposal}, run=run, iteration=iteration)
    lean_verification = _summarise_lean(report.meta)
    p = peer.agent({"report": report.text,
                    "references": references or "(none available)",
                    "lean_verification": lean_verification},
                   run=run, iteration=iteration)
    c = critic.agent({"report": report.text, "lean_verification": lean_verification},
                     run=run, iteration=iteration)
    passed = gate([p.score, c.score], threshold)
    return PubResult(
        report=report.text,
        peer_score=p.score,
        critic_score=c.score,
        peer_text=p.text,
        critic_text=c.text,
        passed=passed,
        report_meta=report.meta,
    )
