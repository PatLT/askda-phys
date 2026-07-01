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
