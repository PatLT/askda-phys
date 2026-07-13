"""Central configuration for ASKDA-Phys.

Everything that you might reasonably want to tune without touching agent logic
lives here: which concrete model backs each tier, the pass/fail thresholds, and
filesystem locations.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


# --------------------------------------------------------------------------- #
# Model tiers
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ModelConfig:
    """How to reach the model that backs a tier."""
    client: str          # registered client name, e.g. "anthropic" | "deepseek" | "ollama" | "mock"
    model: str           # model identifier passed to that client
    temperature: float = 0.7
    max_tokens: int = 4096


# The three tiers from the plan, backed by the Anthropic API by default.
# Model IDs are pinned snapshots (verified against the Claude Platform docs).
# Requires ANTHROPIC_API_KEY in the environment.
#
#   FAST   -> Haiku 4.5  : memeticist, archivist (cheap, short structured output)
#   SMART  -> Sonnet 4.6 : interpreter, sceptic, advisor, supervisor, peer, critic
#   GENIUS -> Opus 4.8   : maniac, leangrad (maximum reasoning)
#
# NOTE on GENIUS: Opus 4.8 is the strongest model with open API access. The
# Mythos-class tier above it (Claude Fable 5 / Mythos 5) would in principle be
# the best fit for `leangrad`, but its API access is currently suspended; swap
# GENIUS to "claude-fable-5" if/when your account has access. Even so, autonomous
# research-level Lean formalisation remains hard - keep the numerical fallback.
ANTHROPIC_TIERS: dict[str, ModelConfig] = {
    "FAST":   ModelConfig("anthropic", "claude-haiku-4-5-20251001", 0.4, 4096),
    "SMART":  ModelConfig("anthropic", "claude-sonnet-4-6",         0.6, 8192),
    "GENIUS": ModelConfig("anthropic", "claude-opus-4-8",           0.8, 16384),
}

DEEPSEEK_TIERS: dict[str, ModelConfig] = {
    "FAST":   ModelConfig("deepseek", "deepseek-v4-flash",  0.4, 4096),
    "SMART":  ModelConfig("deepseek", "deepseek-v4-pro",  0.6, 8192),
    "GENIUS": ModelConfig("deepseek", "deepseek-v4-pro",    0.8, 16384)
}

# Local-model preset (Ollama). Activate with models.use_ollama().
OLLAMA_TIERS: dict[str, ModelConfig] = {
    "FAST":   ModelConfig("ollama", "llama3.2",    0.4, 4096),
    "SMART":  ModelConfig("ollama", "qwen2.5:14b", 0.6, 8192),
    "GENIUS": ModelConfig("ollama", "qwen2.5:32b", 0.8, 16384),
}

# Active tiers. Agents read this; presets above can be swapped in via models.py.
TIERS: dict[str, ModelConfig] = dict(DEEPSEEK_TIERS)


# --------------------------------------------------------------------------- #
# Gating / reattempts
# --------------------------------------------------------------------------- #
# cafeteam (maniac -> interpreter+sceptic) and pubteam (leangrad -> peer+critic)
# both gate their idea agent via `scoring.reattempt_decision` on the summed
# 1-5 reviewer scores (see that function for the ACCEPT/REATTEMPT/REJECT
# rule). These control how many re-tries each idea agent gets before the
# gate is forced to a final ACCEPT/REJECT; attempt is 0-indexed, so the
# default of 2 means up to 3 total attempts.
N_MANIAC_REATTEMPTS: int = 2
N_LEANGRAD_REATTEMPTS: int = 2


# --------------------------------------------------------------------------- #
# Filesystem
# --------------------------------------------------------------------------- #
# Root for everything the library writes. Overridable via the CLI.
DATA_ROOT: Path = Path(".askda")
RUNS_DIR: Path = DATA_ROOT / "runs"
WEB_PATH: Path = DATA_ROOT / "web.json"
MEME_DESC_DIR: Path = DATA_ROOT / "meme_descriptions"


# --------------------------------------------------------------------------- #
# Seed pages for the initial web of knowledge
# --------------------------------------------------------------------------- #
SEED_PAGES: list[str] = [
    "https://en.wikipedia.org/wiki/Metaphysics",
    "https://en.wikipedia.org/wiki/Analytic_philosophy",
    "https://en.wikipedia.org/wiki/Buddhist_philosophy",
    "https://en.wikipedia.org/wiki/Islamic_philosophy",
    "https://en.wikipedia.org/wiki/Taoist_philosophy",
    "https://en.wikipedia.org/wiki/Physics",
    "https://en.wikipedia.org/wiki/Philosophy_of_physics",
    "https://en.wikipedia.org/wiki/Philosophy_of_science",
    "https://en.wikipedia.org/wiki/Cosmology",
    "https://en.wikipedia.org/wiki/Physical_cosmology",
    "https://en.wikipedia.org/wiki/Condensed_matter_physics",
    "https://en.wikipedia.org/wiki/Particle_physics",
    "https://en.wikipedia.org/wiki/Biophysics",
    "https://en.wikipedia.org/wiki/Quantum_information",
]
