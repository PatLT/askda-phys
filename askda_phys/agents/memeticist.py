"""memeticist (FAST) - breaks web nodes into single memetic units.

STATUS: DRAFT. The plan marks this agent's prompt as TBD. The spec below is a
first pass derived from the 'Web of knowledge' section (label nodes MEME vs
COMPLEX; split COMPLEX into MEME nodes; tag philosophy/seed vs application).
Refine `persona`/`objective` before relying on it.
"""
from __future__ import annotations

from .base import Agent, AgentSpec

SPEC = AgentSpec(
    name="memeticist",
    tier="FAST",
    persona=(
        "You are a careful epistemologist who decomposes bodies of knowledge into "
        "their smallest self-contained conceptual units ('memes')."
    ),
    objective=(
        "[DRAFT] Given a node of the knowledge web (a title and short description), "
        "decide whether it is a single memetic unit (MEME) or a composite "
        "(COMPLEX). If COMPLEX, decompose it into a list of constituent MEME units, "
        "each with a title and a one-sentence description. For each unit, label it "
        "as a concept/ontology (a seed for analogy generation) or a phenomenon (an "
        "application target).\n\n"
        "Return JSON: {\"kind\": \"MEME\"|\"COMPLEX\", \"role\": "
        "\"PHILOSOPHY\"|\"APPLICATION\", \"children\": [{\"title\":..., "
        "\"description\":..., \"role\":...}, ...]}. children is empty for MEME."
    ),
    context_template="Node:\nTitle: {title}\nDescription: {description}",
    tool_guidance="May read the source page or run a web search to decompose COMPLEX nodes.",
    reports_score=False,
    tools=("reader", "web_search"),
)

agent = Agent(SPEC)
