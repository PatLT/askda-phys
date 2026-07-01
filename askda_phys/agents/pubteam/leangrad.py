"""leangrad (GENIUS) - PhD student; formalises the proposal in Physlib (Lean 4).

This agent runs the only verifier-in-the-loop in the system - a *linear repair*
loop:
  1. the model drafts a report containing a ```lean block (and optionally a
     ```python block for the numerical solution);
  2. that Lean source is verified; on failure the STRUCTURED errors (see
     tools/physlib) are fed back to the model with the failing source, and it is
     asked for a corrected block; repeat up to MAX_LEAN_ATTEMPTS;
  3. the loop keeps the *best partial* attempt by `LeanResult.progress`, not the
     most recent one, so a proof that compiles-with-`sorry` is preferred over one
     that no longer parses.

This is the pragmatic slice of "verifier-in-the-loop": iterative repair with
error feedback, no best-of-N sampling and no tree search. Verification is never
required for the pipeline to proceed - on exhaustion the numerical (scipy)
fallback carries the result, keeping STRONG status independent of Lean success.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ... import models
from ...tools import physlib, pyexec
from ..base import Agent, AgentResult, AgentSpec

if TYPE_CHECKING:
    from ...orchestration.run import Run

MAX_LEAN_ATTEMPTS = 3

SPEC = AgentSpec(
    name="leangrad",
    tier="GENIUS",
    persona=(
        "You are a PhD-level researcher in theoretical physics. Your highly-"
        "respected supervisor suggests open problems to solve and conceptual "
        "frameworks in which to tackle them. You are familiar with all the methods "
        "of theoretical and mathematical physics. You highly respect your "
        "supervisor's extremely novel conceptual frameworks and cleave as close to "
        "his ideas as possible in your attempts."
    ),
    objective=(
        "You are given an open problem/phenomenon and a proposal for tackling it. "
        "Using the provided conceptual framework, construct a mathematical model. "
        "Translate it into Physlib (Lean 4) and verify its logic; if it fails, "
        "re-attempt, each time incorporating further concepts/results from "
        "established theories relevant to the field. On success, solve the model - "
        "break it down in Physlib to a point where it yields numerical values "
        "directly, or translate it to Python (scipy) for a numerical solution.\n\n"
        "Output a short report: a brief intro (the problem as supplied), a methods "
        "section (which aspects of the conceptual framework survive into the final "
        "model, then the model itself in mathematical notation), a results section "
        "(numerical values vs the quantifiable aspects of the phenomenon), and a "
        "summary (what was and was not captured). Append the Physlib source in a "
        "```lean code block and any numerical solver in a ```python code block."
    ),
    context_template="Your supervisor's research proposal:\n{proposal}",
    tool_guidance=(
        "Use Physlib for proofs; the soundness of the model must be proven in "
        "Physlib. Use Python (scipy) for numerical solutions where needed."
    ),
    reports_score=False,
    tools=("physlib", "pyexec"),
)


class _LeanGrad(Agent):
    def act(self, context, run: "Run | None" = None,
            iteration: int | None = None) -> AgentResult:
        draft = super().act(context, run=run, iteration=iteration)
        proposal = context.get("proposal", "")

        best_src = _extract_block(draft.text, "lean")
        verified = False
        attempts: list[dict] = []

        if best_src:
            current = best_src
            best_result = None
            for i in range(1, MAX_LEAN_ATTEMPTS + 1):
                result = physlib.verify(current)
                attempts.append({"attempt": i, "ok": result.ok,
                                 "summary": result.summary()})
                if best_result is None or result.progress > best_result.progress:
                    best_result, best_src = result, current
                if result.ok:
                    verified = True
                    break
                if not result.attempted:      # no toolchain: no signal to repair on
                    break
                if i < MAX_LEAN_ATTEMPTS:
                    prompt = _repair_prompt(proposal, current, result)
                    fix = models.call(self.spec.tier, prompt, self.system_prompt())
                    if run is not None:
                        run.log(f"{self.spec.name}_repair{i}", prompt, fix,
                                iteration=iteration)
                    current = _extract_block(fix, "lean") or current

        py_src = _extract_block(draft.text, "python")
        numeric = pyexec.run(py_src) if py_src else None

        draft.meta.update({
            "lean_verified": verified,
            "lean_attempts": attempts,
            "lean_source": best_src,
            "numerical_output": _summarise_exec(numeric),
        })
        return draft


def _repair_prompt(proposal: str, source: str, result) -> str:
    errors = "\n".join(
        f"  - line {e.line}: {e.message}" if e.line else f"  - {e.message}"
        for e in result.errors
    ) or "  (no line-level errors parsed; see log)"
    return (
        "Your Physlib (Lean 4) formalisation did not verify. Fix it.\n\n"
        f"Problem context:\n{proposal}\n\n"
        f"Your previous Lean source:\n```lean\n{source}\n```\n\n"
        f"Verifier result: {result.summary()}\n"
        f"Errors:\n{errors}\n\n"
        "Return a corrected, complete Lean formalisation in a single ```lean "
        "code block. Address the specific errors above; you may pull in further "
        "established results if needed. If a lemma is genuinely out of reach, you "
        "may leave a `sorry` rather than an unparseable proof - a file that "
        "elaborates with a sorry is preferred over one that does not compile."
    )


def _summarise_exec(numeric) -> dict | None:
    if numeric is None:
        return None
    return {"ok": numeric.ok, "returncode": numeric.returncode,
            "stdout": (numeric.stdout or "")[:2000]}


def _extract_block(text: str, lang: str) -> str | None:
    """Pull the first fenced ```<lang> ... ``` block out of model output."""
    fence = f"```{lang}"
    start = text.find(fence)
    if start == -1:
        return None
    start += len(fence)
    end = text.find("```", start)
    return text[start:end].strip() if end != -1 else None


agent = _LeanGrad(SPEC)
