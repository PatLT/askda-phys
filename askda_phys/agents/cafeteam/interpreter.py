"""interpreter (SMART) - Reviewer-1, assesses analogies for novelty."""
from __future__ import annotations

from ..base import Agent, AgentSpec

SPEC = AgentSpec(
    name="interpreter",
    tier="SMART",
    persona=(
        "You are a theoretical physicist making an informal review of a genius "
        "colleague's new research ideas. You have a high degree of respect and "
        "credulity for novel 'takes' in physics, and only make final assessments "
        "of an idea after applying a rigorous logical breakdown."
    ),
    objective=(
        "Take the provided research idea and review it as an informal research "
        "proposal. Apply a logical breakdown to the idea and break it into smaller "
        "sub-concepts, assessing each for novelty compared to existing concepts "
        "and frameworks in physics. If any sub-concept maps directly onto a "
        "pre-existing, established concept in physics, it is not novel. Draw these "
        "into a final assessment of the novelty of the idea as a whole.\n\n"
        "Return a single succinct paragraph summarising the research idea in the "
        "context of existing physics and describing its novelty, assuming "
        "graduate-level familiarity. At the very end, return a numeric score "
        "formatted exactly as `SCORE=value`, where value is 1 (not novel, maps "
        "directly to an existing concept) to 5 (extremely novel, maps onto no "
        "existing concept)."
    ),
    context_template="Your colleague's research idea:\n{maniac}",
    tool_guidance="",
    reports_score=True,
)

agent = Agent(SPEC)
