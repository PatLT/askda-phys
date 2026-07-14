"""panelone - advisor (author) + internal, revtwo, bureaucrat (reviewers).

Structurally similar to cafeteam/pubteam (an idea agent re-attempting with
accumulated reviewer feedback each round), but the gate is different: panelone
does NOT accept/reject. It runs advisor through `n_reattempts + 1` attempts -
each subsequent one seeing every prior round's reviews concatenated onto its
original context - and simply returns whichever attempt scored highest
(summed across all three reviewers). Every seed that reaches panelone gets a
best-effort proposal out; there's no rejection to speak of.

The three reviewers' score ranges are deliberately uneven - bureaucrat 0-1,
internal 1-4, revtwo 1-5 - so total_score still tops out at 10, matching
cafeteam/pubteam's own two-reviewer max, while de-weighting internal relative
to revtwo within that budget. Don't "fix" this into three uniform 1-5 scales.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from tqdm import tqdm

from ...config import N_ADVISOR_REATTEMPTS
from ...scoring import total_score
from . import advisor, bureaucrat, internal, revtwo

if TYPE_CHECKING:
    from ...orchestration.run import Run
    from ...tools.data import DataPoint


@dataclass
class PanelAttempt:
    proposal: str
    grounded: list["DataPoint"]  # full CODATA points - value/unit/uncertainty, not just names
    internal_score: float | None
    internal_text: str
    revtwo_score: float | None
    revtwo_text: str
    bureaucrat_score: float | None
    bureaucrat_text: str
    total_score: float


@dataclass
class PanelResult:
    best: PanelAttempt
    attempts: int
    all_attempts: list[PanelAttempt] = field(default_factory=list)


def _feedback_block(rounds: list[str]) -> str:
    """Concatenates all prior rounds' reviewer feedback onto advisor's
    original context; empty on the first attempt, so its prompt is unchanged
    from before this feature existed."""
    if not rounds:
        return ""
    joined = "\n\n".join(f"Round {i + 1} feedback:\n{fb}" for i, fb in enumerate(rounds))
    return f"\n\nPrevious attempt(s) - reviews for reference, revise accordingly:\n{joined}"


def run_panelone(maniac: str, interpreter: str, sceptic: str,
                 run: "Run | None" = None,
                 n_reattempts: int = N_ADVISOR_REATTEMPTS,
                 verbosity: int = 0) -> PanelResult:
    """verbosity >= 2 (debug): trace each attempt the same way
    `cafeteam.run_cafeteam` does - which agent is running, each reviewer's
    score, and the running total for that attempt."""
    feedback_rounds: list[str] = []
    all_attempts: list[PanelAttempt] = []
    best: PanelAttempt | None = None
    total_attempts = n_reattempts + 1

    for attempt in range(total_attempts):
        label = f"[panelone] attempt {attempt + 1}/{total_attempts}"

        if verbosity >= 2:
            tqdm.write(f"{label}: advisor")
        advisor_out = advisor.agent({
            "maniac": maniac,
            "interpreter": interpreter,
            "sceptic": sceptic,
            "feedback": _feedback_block(feedback_rounds),
        }, run=run, iteration=attempt)
        grounded = list(advisor_out.meta.get("grounded", []))

        review_context = {
            "proposal": advisor_out.text,
            "maniac": maniac, "interpreter": interpreter, "sceptic": sceptic,
        }

        if verbosity >= 2:
            tqdm.write(f"{label}: internal")
        i_out = internal.agent(review_context, run=run, iteration=attempt)
        if verbosity >= 2:
            tqdm.write(f"{label}: internal SCORE={i_out.score}")

        if verbosity >= 2:
            tqdm.write(f"{label}: revtwo")
        r_out = revtwo.agent(review_context, run=run, iteration=attempt)
        if verbosity >= 2:
            tqdm.write(f"{label}: revtwo SCORE={r_out.score}")

        if verbosity >= 2:
            tqdm.write(f"{label}: bureaucrat")
        b_out = bureaucrat.agent(review_context, run=run, iteration=attempt)
        if verbosity >= 2:
            tqdm.write(f"{label}: bureaucrat SCORE={b_out.score}")

        total = total_score([i_out.score, r_out.score, b_out.score])
        current = PanelAttempt(
            proposal=advisor_out.text,
            grounded=grounded,
            internal_score=i_out.score, internal_text=i_out.text,
            revtwo_score=r_out.score, revtwo_text=r_out.text,
            bureaucrat_score=b_out.score, bureaucrat_text=b_out.text,
            total_score=total,
        )
        all_attempts.append(current)
        if verbosity >= 2:
            tqdm.write(f"{label}: total={total}"
                      + (" (new best)" if best is None or total > best.total_score else ""))
        if best is None or current.total_score > best.total_score:
            best = current

        if attempt < total_attempts - 1:
            feedback_rounds.append(
                f"Internal review: {i_out.text}\n\n"
                f"Second reviewer: {r_out.text}\n\n"
                f"Bureaucratic review: {b_out.text}")

    assert best is not None  # loop always runs >= 1 time (n_reattempts >= 0)
    return PanelResult(best=best, attempts=total_attempts, all_attempts=all_attempts)
