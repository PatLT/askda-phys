"""cafeteam - the idea team: maniac (author) + interpreter + sceptic (reviewers).

`run_cafeteam` executes maniac's analogy through interpreter (novelty) and
sceptic (credibility), re-attempting up to `n_reattempts` times - with the
reviewers' own reports fed back to maniac each time - before settling on a
final ACCEPT/REJECT via `scoring.reattempt_decision`. Mirrors `pubteam`'s
leangrad/peer/critic loop one level up the pipeline (maniac is the "idea
agent" here the way leangrad is the "idea agent" there).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ...config import N_MANIAC_REATTEMPTS
from ...scoring import reattempt_decision, total_score
from . import interpreter, maniac, sceptic

if TYPE_CHECKING:
    from ...orchestration.run import Run


@dataclass
class CafeResult:
    analogy: str
    novelty_score: float | None
    credibility_score: float | None
    novelty_text: str
    credibility_text: str
    passed: bool
    attempts: int
    total_score: float


def _feedback_block(rounds: list[str]) -> str:
    """Concatenates all prior rounds' reviewer feedback onto maniac's original
    seed context; empty on the first attempt, so its prompt is unchanged from
    before this feature existed."""
    if not rounds:
        return ""
    joined = "\n\n".join(f"Round {i + 1} feedback:\n{fb}" for i, fb in enumerate(rounds))
    return f"\n\nPrevious attempt(s) were not accepted. Revise based on this feedback:\n{joined}"


def run_cafeteam(title: str, description: str, run: "Run | None" = None,
                 n_reattempts: int = N_MANIAC_REATTEMPTS) -> CafeResult:
    feedback_rounds: list[str] = []
    analogy = interp = skep = None
    total = 0.0
    for attempt in range(n_reattempts + 1):
        analogy = maniac.agent(
            {"title": title, "description": description,
             "feedback": _feedback_block(feedback_rounds)},
            run=run, iteration=attempt)
        interp = interpreter.agent({"maniac": analogy.text}, run=run, iteration=attempt)
        skep = sceptic.agent({"maniac": analogy.text}, run=run, iteration=attempt)

        total = total_score([interp.score, skep.score])
        decision = reattempt_decision(total, attempt, n_reattempts)
        if decision != "REATTEMPT":
            return CafeResult(analogy.text, interp.score, skep.score,
                             interp.text, skep.text, decision == "ACCEPT",
                             attempt + 1, total)
        feedback_rounds.append(
            f"Novelty review (interpreter): {interp.text}\n\n"
            f"Credibility review (sceptic): {skep.text}")

    # unreachable: reattempt_decision always resolves ACCEPT/REJECT by
    # attempt == n_reattempts (see its docstring); kept as a defensive fallback.
    return CafeResult(analogy.text, interp.score, skep.score, interp.text, skep.text,
                      False, n_reattempts + 1, total)
