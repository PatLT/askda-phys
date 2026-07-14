"""bureaucrat (SMART) - panelone reviewer. SKELETON: persona/objective are TBD.

Reviews advisor's proposal (`{proposal}`); returns a short paragraph plus a
`SCORE=value` (1-5) line, same convention as interpreter/sceptic/peer/critic.
"""
from __future__ import annotations

from ..base import Agent, AgentSpec

SPEC = AgentSpec(
    name="bureaucrat",
    tier="SMART",
    persona=(
        "TBD."
    ),
    objective=(
        "TBD.\n\n"
        "Return a single short paragraph review. At the very end, return a "
        "numeric score formatted exactly as `SCORE=value`, where value is 1 "
        "(TBD) to 5 (TBD)."
    ),
    context_template=(
        "Research proposal to review:\n{proposal}"
    ),
    tool_guidance="",
    reports_score=True,
)

agent = Agent(SPEC)
