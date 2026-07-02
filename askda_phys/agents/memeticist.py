"""memeticist (FAST) - breaks web nodes into single memetic units.

Per the plan's 'Web of knowledge' section: traverses the web, labels each node
MEME (a single memetic unit fit to seed `maniac`) or COMPLEX, splits COMPLEX
nodes into MEME children, and tags every MEME with a role - CONCEPT (an
ontology/idea, i.e. a seed for analogy generation) or PHENOMENON (an
application target), or OTHER if it's neither (e.g. a proper noun). The
traversal itself lives in `knowledge/memetic.py`.
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
        "Given a node of the knowledge web (a title and short description), "
        "decide whether it is a single memetic unit (MEME) or a composite of "
        "several distinct ideas (COMPLEX).\n\n"
        "If COMPLEX, decompose it into a list of constituent MEME units, each "
        "with its own title and a one-sentence description precise enough to "
        "stand alone as a seed concept.\n\n"
        "For every MEME unit (the node itself, if it is already a MEME, or each "
        "child of a COMPLEX node), classify its role: CONCEPT if it names an idea "
        "or ontology that could seed an analogy, PHENOMENON if it names an "
        "observed effect or problem an analogy could be applied to, or OTHER if "
        "it is neither (e.g. a proper noun - a person, place, school, or work).\n\n"
        "Return JSON only, no prose: {\"kind\": \"MEME\"|\"COMPLEX\", \"role\": "
        "\"CONCEPT\"|\"PHENOMENON\"|\"OTHER\", \"children\": [{\"title\":..., "
        "\"description\":..., \"role\": \"CONCEPT\"|\"PHENOMENON\"|\"OTHER\"}, "
        "...]}. children must be empty when kind is MEME."
    ),
    context_template="Node:\nTitle: {title}\nDescription: {description}",
    tool_guidance="May read the source page or run a web search to decompose COMPLEX nodes.",
    reports_score=False,
    tools=("reader", "web_search"),
)

agent = Agent(SPEC)
