"""Literature review tool: ask a natural-language research question and get
back a citation-backed literature review. paper-qa's own agent only
searches/retrieves/synthesizes over a local paper directory - it has no web
download step of its own - so this module fetches real candidate papers from
arXiv (tools/paperfetch.py) before handing off to paper-qa.

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

paper-qa's local paper_directory defaults to Path.cwd() when unset, which
would otherwise mean every call recursively indexes this whole repo -
including our own .askda/runs/*.txt agent transcripts - as if it were a
paper corpus. `_settings` pins it to config.PAPERQA_PAPER_DIR instead. But
paper-qa itself never downloads anything into that directory - it only ever
searches whatever's already there - so `literature_review` calls
`tools.paperfetch.fetch_papers` first to actually populate it from arXiv.

`literature_review` returns `(answer_text, citations)`: `citations` is a
plain list of bibliographic strings for only the papers paper-qa's own
`session.used_contexts` says were actually cited in the answer, read off
`DocDetails.citation` for each cited context - not asked of the LLM, so it
can be trusted and concatenated directly into a report rather than relying
on the model to reproduce it faithfully (see agents/tooling.py's `_paperqa`,
which threads this through `AgentResult.meta["citations"]` rather than the
observation text the model sees).

paper-qa (and litellm underneath it) are very chatty - progress output plus a
lot of logging, including citation/metadata-lookup warnings from resolving
references against Crossref, which are mostly benign noise from its own
internal search machinery rather than a sign anything we sent it is wrong.
`literature_review` redirects all of that to `config.PAPERQA_LOG_PATH`
(append mode) at the OS file-descriptor level rather than just reassigning
`sys.stdout`/`sys.stderr` - some of that logging is bound to the *original*
stderr object before we ever get a chance to redirect it, so a plain
`contextlib.redirect_stdout` wouldn't reliably catch it.
"""
from __future__ import annotations

import contextlib
import os
import sys
from typing import TYPE_CHECKING

from ..config import PAPERQA_LOG_PATH, PAPERQA_PAPER_DIR, TIERS

if TYPE_CHECKING:  # type-only: the real imports are deferred below (heavy - litellm etc.)
    from paperqa import Settings
    from paperqa.agents.models import AnswerResponse


@contextlib.contextmanager
def _redirect_fds_to_file(path):
    """Redirect OS-level stdout/stderr (fd 1/2) to `path` for the block,
    restoring them afterward. Catches output from anything writing to those
    file descriptors directly - print(), logging handlers configured before
    this call, subprocess output - not just code that looks up
    sys.stdout/sys.stderr fresh each time.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    sys.stdout.flush()
    sys.stderr.flush()
    saved_out_fd = os.dup(1)
    saved_err_fd = os.dup(2)
    with open(path, "a") as f:
        os.dup2(f.fileno(), 1)
        os.dup2(f.fileno(), 2)
        try:
            yield
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            os.dup2(saved_out_fd, 1)
            os.dup2(saved_err_fd, 2)
            os.close(saved_out_fd)
            os.close(saved_err_fd)

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
    PAPERQA_PAPER_DIR.mkdir(parents=True, exist_ok=True)
    return Settings(
        llm=model,
        summary_llm=model,
        embedding=EMBEDDING_MODEL,
        agent={
            "agent_llm": model,
            "index": {
                "paper_directory": str(PAPERQA_PAPER_DIR),
                "recurse_subdirectories": False,
            },
        },  # type: ignore
    )


def literature_review(question: str, *, tier: str = "SMART") -> tuple[str, list[str]]:
    """Ask a natural-language research question; fetches real candidate
    papers from arXiv into PAPERQA_PAPER_DIR, then lets paper-qa's own agent
    search that local corpus, retrieve relevant passages, and synthesize a
    citation-backed answer.

    Returns `(answer_text, citations)` - `answer_text` is the formatted
    answer (prose + paper-qa's own inline references), or a clearly-flagged
    partial result if paper-qa didn't reach a confident answer (rather than
    silently returning a weak answer as if it were solid); `citations` is
    the plain-string bibliography for only the papers actually cited,
    suitable for direct (non-LLM) concatenation into a report - see the
    module docstring.
    """
    from paperqa import ask  # deferred: heavy import (litellm etc.)
    from paperqa.agents.models import AnswerResponse

    from . import paperfetch

    settings = _settings(tier)
    try:
        paperfetch.fetch_papers(question)
    except Exception:
        pass  # a fetch hiccup shouldn't block querying whatever's already local

    with _redirect_fds_to_file(PAPERQA_LOG_PATH):
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
                f"status={response.status.value})\n\n{session.formatted_answer}", [])
    cited_ids = session.used_contexts
    citations = sorted({c.text.doc.citation for c in session.contexts if c.id in cited_ids})
    return session.formatted_answer, citations
