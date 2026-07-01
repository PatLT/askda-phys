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
    client: str          # registered client name, e.g. "anthropic" | "ollama" | "mock"
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

# Local-model preset (Ollama). Activate with models.use_ollama().
OLLAMA_TIERS: dict[str, ModelConfig] = {
    "FAST":   ModelConfig("ollama", "llama3.2",    0.4, 4096),
    "SMART":  ModelConfig("ollama", "qwen2.5:14b", 0.6, 8192),
    "GENIUS": ModelConfig("ollama", "qwen2.5:32b", 0.8, 16384),
}

# Active tiers. Agents read this; presets above can be swapped in via models.py.
TIERS: dict[str, ModelConfig] = dict(ANTHROPIC_TIERS)


# --------------------------------------------------------------------------- #
# Gating thresholds
# --------------------------------------------------------------------------- #
# Idea survives the interpreter/sceptic gate if the mean of the two scores is
# at or above this value (scores are 1..5).
IDEA_GATE_THRESHOLD: float = 3.0

# Formalisation survives the peer/critic gate at or above this mean.
PUB_GATE_THRESHOLD: float = 3.0


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
