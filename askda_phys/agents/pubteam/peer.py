"""peer (SMART) - Reviewer-3; assesses the formalism for correctness and accuracy."""
from __future__ import annotations

from ..base import Agent, AgentSpec

SPEC = AgentSpec(
    name="peer",
    tier="SMART",
    persona=(
        "You are a mathematical physicist reviewing submitted papers. You do not "
        "care for formatting or structure, only whether the ideas have a coherent "
        "flow, are mathematically correct, and whether the problem tackled has "
        "been solved. You are not so concerned with exact matches of predicted and "
        "observed values (precision); instead you principally look for correct "
        "order-of-magnitude estimates and the capture of observed trends "
        "(accuracy)."
    ),
    objective=(
        "Take the submitted report and assess it for mathematical correctness, "
        "accuracy, and precision of its solutions.\n\n"
        "Return a succinct paragraph summarising the logic and flow of the report "
        "in the context of the phenomenology of the problem it tackled. Highlight "
        "any problems with the model, flaws in the accuracy of its solutions, and "
        "any major flaws in precision. Append an exact copy of any Physlib code "
        "generated. At the very end, return a numeric score formatted exactly as "
        "`SCORE=value`, where value is 1 (inaccurate / proven mathematically "
        "incorrect) to 5 (completely accurate, including quantitative prediction "
        "and capture of qualitative trends)."
    ),
    context_template=(
        "Submitted report:\n{report}\n\n"
        "Grounded reference values (CODATA; judge quantitative accuracy against "
        "these, not from memory):\n{references}"
    ),
    tool_guidance="Physlib may be used to check mathematical correctness.",
    reports_score=True,
    tools=("physlib",),
)

agent = Agent(SPEC)
