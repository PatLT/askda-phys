"""ASKDA-Phys: Agents for knowledge Systemisation and Discovery-by-Analogy in Physics."""
from __future__ import annotations

__version__ = "0.0.1"

from . import agents, config, models, scoring  # noqa: F401
from .knowledge import (KnowledgeWeb, add_semantic_links, best_seed,
                        build_initial_web, ensure_description, rank_seeds, trawl_web)
from .orchestration import (DiscoveryResult, Run, discover, run_stage0_ranking,
                            run_stage1, run_stage1_advisor_only)

__all__ = [
    "config",
    "models",
    "scoring",
    "agents",
    "KnowledgeWeb",
    "build_initial_web",
    "trawl_web",
    "add_semantic_links",
    "ensure_description",
    "rank_seeds",
    "best_seed",
    "Run",
    "discover",
    "DiscoveryResult",
    "run_stage0_ranking",
    "run_stage1",
    "run_stage1_advisor_only",
]
