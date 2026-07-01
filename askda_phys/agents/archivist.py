"""archivist (FAST) - inserts findings into the web of knowledge.

STATUS: DRAFT. The plan marks this agent's prompt as TBD. Per the plan, only the
node-mapping step is agentic: given the seed idea, the field of application, and
the exact problem, map the problem to an existing web node or define a new one.
The edge creation and FAILED/WEAK/STRONG labelling are deterministic and handled
by the orchestrator (see orchestration/pipeline.py), not by the model.
"""
from __future__ import annotations

from .base import Agent, AgentSpec

SPEC = AgentSpec(
    name="archivist",
    tier="FAST",
    persona=(
        "You are a meticulous archivist maintaining a directed graph of concepts "
        "in physics and philosophy."
    ),
    objective=(
        "[DRAFT] You are given the seed concept, the field of application, and the "
        "exact problem the analogy was applied to. Decide whether the problem "
        "corresponds to one of the provided existing application nodes, or whether "
        "a new node should be created.\n\n"
        "Return JSON: {\"match\": \"<existing node id>\"|null, \"new_node\": "
        "{\"title\":..., \"description\":...}|null}. Provide exactly one of "
        "`match` or `new_node`."
    ),
    context_template=(
        "Seed concept:\n{seed}\n\n"
        "Field of application:\n{field}\n\n"
        "Exact problem:\n{problem}\n\n"
        "Candidate existing application nodes:\n{candidates}"
    ),
    tool_guidance="",
    reports_score=False,
)

agent = Agent(SPEC)
