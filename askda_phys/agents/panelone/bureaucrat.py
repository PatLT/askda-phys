"""bureaucrat (SMART) - panelone reviewer: a binary feasibility gate - can the
proposal actually be completed with the downstream pipeline's own tools
(Physlib/Lean, then scipy)? Returns a short paragraph plus a `SCORE=value`
(0 or 1) line.
"""
from __future__ import annotations

from ..base import Agent, AgentSpec

SPEC = AgentSpec(
    name="bureaucrat",
    tier="SMART",
    persona=(
        "You are an administrative worker at a large research facility. "
        "You assess research proposals on simple criteria - whether or not "
        "they are feasible with the tools available to the researchers. "
        "Other facets of the proposal do not concern you. "
    ),
    objective=(
        "Review the attached research proposal for feasibility. It is feasible "
        "if it is possible to complete the proposed project using the following "
        "tools: (1) mathematical manipulation, strictly formulated in and solved "
        "using lean (including physlib); (2) numerical solution of resulting models, "
        "which will be coded in python using scipy as the primary library "
        "for solvers.\n\n"
        "Return a single short paragraph assessment. At the very end, return a "
        "numeric score formatted exactly as `SCORE=value`, where value is 0 "
        "(not feasible) or 1 (feasible)."
    ),
    context_template=(
        "Research proposal to review:\n{proposal}"
    ),
    tool_guidance="",
    reports_score=True,
)

agent = Agent(SPEC)
