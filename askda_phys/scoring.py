"""Shared scoring + gate logic.

Reviewer agents (interpreter, sceptic, peer, critic) end their output with a
line of the form `SCORE=value`. This module extracts that and decides gates.
"""
from __future__ import annotations

import re
from statistics import mean

_SCORE_RE = re.compile(r"SCORE\s*=\s*([1-5](?:\.\d+)?)", re.IGNORECASE)


def parse_score(text: str) -> float | None:
    """Return the last `SCORE=` value in `text`, or None if absent.

    The last occurrence wins so that a model quoting the instruction earlier in
    its answer doesn't shadow its actual verdict.
    """
    matches = _SCORE_RE.findall(text or "")
    return float(matches[-1]) if matches else None


def gate(scores: list[float | None], threshold: float) -> bool:
    """Pass if the mean of present scores meets `threshold`.

    Missing scores (None) are treated as failures-to-report and excluded from
    the mean; if *no* score is present at all, the gate fails closed.
    """
    present = [s for s in scores if s is not None]
    if not present:
        return False
    return mean(present) >= threshold


def total_score(scores: list[float | None]) -> float:
    """Sum of two 1-5 reviewer scores (range 2-10); a missing score counts 0."""
    return sum(s or 0.0 for s in scores)


def reattempt_decision(total: float, attempt: int, n_reattempts: int) -> str:
    """ACCEPT | REATTEMPT | REJECT for cafeteam/pubteam's idea-agent loop.

    `attempt` is 0-indexed (0 = first/initial attempt); `n_reattempts` re-tries
    are allowed after it, so the loop's final attempt has attempt == n_reattempts.

        total >= 8                                       -> ACCEPT
        total >= 7 and attempt == n_reattempts            -> ACCEPT (last shot, good enough)
        3 <= total < 8 and attempt < n_reattempts         -> REATTEMPT
        3 <= total < 7 and attempt >= n_reattempts         -> REJECT (out of attempts)
        total < 3                                          -> REJECT (never worth retrying)

    Exhaustive for attempt in [0, n_reattempts]: at attempt == n_reattempts the
    ranges collapse to ACCEPT for total >= 7, REJECT below - REATTEMPT is only
    ever returned while attempts remain.
    """
    if total >= 8:
        return "ACCEPT"
    if total >= 7 and attempt == n_reattempts:
        return "ACCEPT"
    if 3 <= total < 8 and attempt < n_reattempts:
        return "REATTEMPT"
    if 3 <= total < 7 and attempt >= n_reattempts:
        return "REJECT"
    return "REJECT"  # total < 3
