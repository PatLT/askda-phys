"""Literature review tool: ask a natural-language research question and get
back a citation-backed literature review, via paper-qa's own web-search ->
download -> retrieve -> synthesize agent.

Configured to reuse whichever backend/tier is currently active for the rest
of askda_phys (see config.TIERS) for all three of paper-qa's LLM roles - the
main QA synthesis, per-paper summarization, and the tool-use loop that drives
the search - via LiteLLM's native provider routing (deepseek/, anthropic/,
ollama/). Switching the rest of the system's backend
(models.use_anthropic()/use_deepseek()/use_ollama()) switches this tool too.

The embedding model is a deliberate exception: neither Anthropic nor DeepSeek
offer an embeddings API, so chunk retrieval always goes through a local
Ollama model (nomic-embed-text, 274MB) regardless of which backend is active
for chat. This needs `ollama pull nomic-embed-text` and the Ollama server
running (`ollama serve`) - independent of whether Ollama is the active chat
backend for the rest of the system.

paper-qa has no offline/mock mode - it does real web search and paper
download - so this tool refuses to run under the mock backend rather than
pretending to.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..config import TIERS

if TYPE_CHECKING:  # type-only: the real imports are deferred below (heavy - litellm etc.)
    from paperqa import Settings
    from paperqa.agents.models import AnswerResponse

EMBEDDING_MODEL = "ollama/nomic-embed-text"

_LITELLM_PROVIDER = {
    "anthropic": "anthropic",
    "deepseek": "deepseek",
    "ollama": "ollama",
}


def _litellm_model(tier: str) -> str:
    """Map an askda_phys tier (FAST/SMART/GENIUS) to a LiteLLM-routable model
    string for whichever backend is currently active (config.TIERS)."""
    cfg = TIERS[tier]
    provider = _LITELLM_PROVIDER.get(cfg.client)
    if provider is None:
        raise RuntimeError(
            f"literature_review: no real backend active for tier {tier!r} "
            f"(client={cfg.client!r}). paper-qa does real web search and "
            f"paper retrieval, so it has no mock/offline equivalent - call "
            f"models.use_anthropic()/use_deepseek()/use_ollama() first.")
    return f"{provider}/{cfg.model}"


def _settings(tier: str) -> Settings:
    from paperqa import Settings  # deferred: heavy import (litellm etc.)

    model = _litellm_model(tier)
    return Settings(
        llm=model,
        summary_llm=model,
        embedding=EMBEDDING_MODEL,
        agent={"agent_llm": model}, # type: ignore
    )


def literature_review(question: str, *, tier: str = "SMART") -> str:
    """Ask a natural-language research question; paper-qa searches the web
    for relevant papers, downloads and retrieves relevant passages, and
    synthesizes a citation-backed answer.

    Returns the formatted answer (prose + references) as a single string, or
    a clearly-flagged partial result if paper-qa didn't reach a confident
    answer (rather than silently returning a weak answer as if it were solid).
    """
    from paperqa import ask  # deferred: heavy import (litellm etc.)
    from paperqa.agents.models import AnswerResponse

    settings = _settings(tier)
    response = ask(question, settings=settings)
    # ask() is typed to return AnswerResponse | asyncio.Task[AnswerResponse] -
    # a Task only if called from inside a running event loop. This codebase is
    # fully synchronous, so it's always the resolved AnswerResponse; assert
    # that rather than silently relying on it, and narrow the type for
    # type-checkers in the process.
    assert isinstance(response, AnswerResponse), (
        "paper-qa returned an asyncio.Task - literature_review() was called "
        "from inside a running event loop, which askda_phys doesn't support.")
    session = response.session

    if not session.has_successful_answer:
        return (f"(literature review did not reach a confident answer - "
                f"status={response.status.value})\n\n{session.formatted_answer}")
    return session.formatted_answer
