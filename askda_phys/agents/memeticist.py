"""memeticist (FAST) - classifies and decomposes web nodes.

Per the plan's 'Web of knowledge' section, this is two calls, not one, so the
expensive decomposition step is only ever paid for nodes that can actually
source a seed for `maniac` - either directly (a concept) or by leading to one
(a school of thought or a philosopher's associated ideas):

  1. `classify_agent` - cheap, no tools. Given a node, decides its role only,
     from seven values (see `_ROLE_GUIDE`): PHILOSOPHY_CONCEPT, PHILOSOPHY_SCHOOL,
     PHILOSOPHER, SCIENCE_CONCEPT, SCIENTIST, PHENOMENON, OTHER. Every node
     gets this once.

  2. `expand_agent` - the heavier, tool-using call. Only invoked (by
     `knowledge/memetic.py`) for nodes classified PHILOSOPHY_CONCEPT,
     PHILOSOPHY_SCHOOL, or PHILOSOPHER that are still COMPLEX: decides whether
     the node is actually a single memetic unit (MEME) or should be split
     into MEME children. SCIENCE_CONCEPT / SCIENTIST / PHENOMENON / OTHER
     nodes never reach this step - they cannot themselves seed an analogy, so
     decomposing them buys nothing.
"""
from __future__ import annotations

from .base import Agent, AgentSpec

ALL_ROLES = frozenset({
    "PHILOSOPHY_CONCEPT", "PHILOSOPHY_SCHOOL", "PHILOSOPHER",
    "SCIENCE_CONCEPT", "SCIENTIST", "PHENOMENON", "OTHER",
})

# Roles that can source a seed for `maniac`, directly (PHILOSOPHY_CONCEPT) or
# by leading to one on decomposition (PHILOSOPHY_SCHOOL, PHILOSOPHER). Kept
# here so `knowledge/memetic.py` can import the same set `trawl_web` expands.
EXPANDABLE_ROLES = frozenset({"PHILOSOPHY_CONCEPT", "PHILOSOPHY_SCHOOL", "PHILOSOPHER"})

_ROLE_JSON = ("\"PHILOSOPHY_CONCEPT\"|\"PHILOSOPHY_SCHOOL\"|\"PHILOSOPHER\"|"
             "\"SCIENCE_CONCEPT\"|\"SCIENTIST\"|\"PHENOMENON\"|\"OTHER\"")

_ROLE_GUIDE = (
    "Classify it into exactly one role:\n"
    "- PHILOSOPHY_CONCEPT: a single idea or ontology from philosophy "
    "(metaphysics, epistemology, philosophy of science, etc.) that could "
    "plausibly seed an analogy to physics.\n"
    "- PHILOSOPHY_SCHOOL: a broader tradition, movement, or school of "
    "philosophical thought (e.g. 'Stoicism', 'Buddhist philosophy', 'Analytic "
    "philosophy') - too broad to be a single seed itself, but its own page "
    "links to the concrete PHILOSOPHY_CONCEPT ideas that make it up.\n"
    "- PHILOSOPHER: a person primarily known for philosophical work - not a "
    "seed itself, but their page links to the concepts and/or school they "
    "are associated with.\n"
    "- SCIENCE_CONCEPT: a theoretical or conceptual construct belonging to "
    "physics/science itself (e.g. 'symmetry', 'entropy', 'gauge invariance') "
    "- real science, but not philosophy, and therefore never used as a seed.\n"
    "- SCIENTIST: a person primarily known for scientific work - not a seed, "
    "and (unlike PHILOSOPHER) not decomposed further.\n"
    "- PHENOMENON: an observed physical effect, system, or problem (e.g. "
    "'superconductivity') - a target an analogy could be applied to, not a "
    "seed.\n"
    "- OTHER: none of the above (e.g. a place or a specific work/text)."
)

CLASSIFY_SPEC = AgentSpec(
    name="memeticist_classify",
    tier="FAST",
    persona=(
        "You are a careful epistemologist who sorts bodies of knowledge by "
        "field and by kind - distinguishing philosophical ideas, schools, and "
        "philosophers from scientific concepts, scientists, and observed "
        "physical phenomena."
    ),
    objective=(
        "Given a node of the knowledge web (a title and short description), "
        f"{_ROLE_GUIDE}\n\n"
        f"Return JSON only, no prose: {{\"role\": {_ROLE_JSON}}}."
    ),
    context_template="Node:\nTitle: {title}\nDescription: {description}",
    tool_guidance="",
    reports_score=False,
)

EXPAND_SPEC = AgentSpec(
    name="memeticist_expand",
    tier="FAST",
    persona=(
        "You are a careful epistemologist who decomposes bodies of knowledge into "
        "their smallest self-contained conceptual units ('memes')."
    ),
    objective=(
        "You are given a node of the knowledge web already identified as one "
        "of PHILOSOPHY_CONCEPT, PHILOSOPHY_SCHOOL, or PHILOSOPHER - something "
        "that can itself seed an analogy, or whose page leads to what can. "
        "Decide whether it is already a single memetic unit (MEME) or a "
        "composite of several distinct ideas (COMPLEX).\n\n"
        "If COMPLEX, decompose it into a list of constituent MEME units. For "
        "a PHILOSOPHY_CONCEPT, this means its constituent sub-ideas. For a "
        "PHILOSOPHY_SCHOOL or PHILOSOPHER, this means the concrete concepts "
        "(and, where relevant, the specific philosophers or schools) "
        "associated with it. Give each unit its own title and a one-sentence "
        "description precise enough to stand alone as a seed concept. Each "
        f"child may take a different role than its parent - {_ROLE_GUIDE}\n\n"
        "Return JSON only, no prose: {\"kind\": \"MEME\"|\"COMPLEX\", "
        "\"children\": [{\"title\":..., \"description\":..., \"role\": "
        f"{_ROLE_JSON}}}, ...]}}. children must be empty when kind is MEME."
    ),
    context_template="Node:\nTitle: {title}\nDescription: {description}",
    tool_guidance="May read the source page or run a web search to decompose COMPLEX nodes.",
    reports_score=False,
    tools=("reader", "web_search"),
    tool_loop=True,
)

classify_agent = Agent(CLASSIFY_SPEC)
expand_agent = Agent(EXPAND_SPEC)
