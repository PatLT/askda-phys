"""ASKDA-Phys: Agents for knowledge Systemisation and Discovery-by-Analogy in Physics."""
from __future__ import annotations

__version__ = "0.0.1"

from . import agents, config, models, scoring  # noqa: F401
from .knowledge import KnowledgeWeb, best_seed, build_initial_web, rank_seeds, trawl_web
from .orchestration import DiscoveryResult, Run, discover

__all__ = [
    "config",
    "models",
    "scoring",
    "agents",
    "KnowledgeWeb",
    "build_initial_web",
    "trawl_web",
    "rank_seeds",
    "best_seed",
    "Run",
    "discover",
    "DiscoveryResult",
]
