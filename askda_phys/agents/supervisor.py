"""supervisor (SMART) - Supervisor-2; proposes an OPEN problem the analogy maps onto.

Per the plan, this does the same job as `advisor` except it (a) ingests the
leangrad report plus the peer and critic reviews instead of the raw analogy,
and (b) only proposes open problems (including un-modelled or crudely-modelled
phenomena) rather than closed ones. Spec below adapts `advisor` accordingly.
"""
from __future__ import annotations

from .base import AgentSpec
from .grounded import GroundedProposalAgent

SPEC = AgentSpec(
    name="supervisor",
    tier="SMART",
    persona=(
        "You are a senior theoretical physicist with broad interests across the "
        "domains of theoretical physics, their intersections, and conceptual "
        "transfer between them, plus the application of physics-derived frameworks "
        "to other modelling domains. You have just read a successful first "
        "formalisation by your student and want to push the same conceptual "
        "framework onto a genuinely open problem."
    ),
    objective=(
        "Take the student's report and the peer/critic reviews and propose "
        "four OPEN problems/phenomena (including un-modelled or only crudely-"
        "modelled phenomena) to which the same conceptual framework could apply. "
        "Each must be tractable to mathematical modelling. From the four, return "
        "the single best fit as a research proposal with the same three-section "
        "structure and mathematical-rigour requirements as a standard proposal.\n\n"
        "GROUNDING: for any fundamental physical constant, write a placeholder "
        "`{{const: <standard CODATA name>}}` rather than a remembered number; the "
        "system substitutes the exact value. Note that open problems are often "
        "under-measured, so where no reliable value exists, state the best "
        "available bound or order-of-magnitude constraint and label it as such."
    ),
    context_template=(
        "Student's report:\n{report}\n\n"
        "Accuracy review (peer):\n{peer}\n\n"
        "Novelty review (critic):\n{critic}"
    ),
    tool_guidance=("Web search may be used to confirm a problem is genuinely "
                   "open. Fundamental constants are grounded in CODATA via "
                   "{{const: ...}} placeholders."),
    reports_score=False,
    tools=("web_search", "data"),
)

agent = GroundedProposalAgent(SPEC)
