"""archivist (FAST) - inserts findings into the web of knowledge.

Per the plan, only the node-mapping step is agentic: given the seed idea, the
field of application, and the exact problem, map the problem to an existing
web node or define a new one. The edge creation and FAILED/WEAK/STRONG
labelling are deterministic and handled by the orchestrator (see
orchestration/pipeline.py), not by the model.
"""
from __future__ import annotations

from .base import Agent, AgentSpec

SPEC = AgentSpec(
    name="archivist",
    tier="FAST",
    persona=(
        "You are a meticulous archivist maintaining a directed graph of concepts "
        "in physics and philosophy. You do not care for prose or justification, "
        "only for placing each new finding at the correct node."
    ),
    objective=(
        "You are given the seed concept, the field of application, and the "
        "exact problem the analogy was applied to, along with a list of "
        "candidate existing application (PHENOMENON) nodes already in the web. "
        "Decide whether the problem corresponds to one of the candidates, or "
        "whether it is distinct enough to warrant a new node.\n\n"
        "Return JSON only, no prose: {\"match\": \"<existing node id>\"|null, "
        "\"new_node\": {\"title\":..., \"description\":...}|null}. Provide "
        "exactly one of `match` or `new_node`, never both, never neither."
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
