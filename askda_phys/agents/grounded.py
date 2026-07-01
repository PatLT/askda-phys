"""Agent mix-in that grounds proposal text in CODATA constants.

Used by `advisor` and `supervisor`. After the model writes its proposal (with
`{{const: ...}}` placeholders), this substitutes exact CODATA values and stashes
the resolved `DataPoint`s in `result.meta["grounded"]` so the pipeline can carry
them to `peer` for a real accuracy comparison.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..tools import data
from .base import Agent, AgentResult

if TYPE_CHECKING:
    from ..orchestration.run import Run


class GroundedProposalAgent(Agent):
    def act(self, context: dict[str, str], run: "Run | None" = None,
            iteration: int | None = None) -> AgentResult:
        res = super().act(context, run=run, iteration=iteration)
        grounded_text, points = data.ground_text(res.text)
        res.text = grounded_text
        res.meta["grounded"] = points
        return res
