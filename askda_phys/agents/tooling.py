"""Tool executors + wire protocol for the generic tool-call loop in `Agent.act()`.

Protocol: a tool-calling agent may respond with, as the *entire* response:

    TOOL: <name>
    <argument>

`Agent.act()` (base.py) detects this, runs the named tool, and feeds the
observation back for another turn - up to `MAX_TOOL_TURNS` times - before the
model must give its real, final answer. Any response that doesn't start with
`TOOL:` is treated as final immediately, so untouched (non-tool) agents and the
offline `MockClient` are unaffected: they never emit that prefix.
"""
from __future__ import annotations

import re
from typing import Callable

from ..tools import paperqa, physlib, pyexec, reader, search

MAX_TOOL_TURNS = 3
_MAX_OBSERVATION_CHARS = 4000

_TOOL_CALL_RE = re.compile(r"^TOOL:\s*(\w+)\s*(.*)", re.DOTALL)
# A model that fabricates a whole fake tool-dialogue (multiple TOOL: lines,
# invented Observation: text) in one completion must not have all of that
# swallowed as a single giant argument - bound the capture at the next
# TOOL:-prefixed line, if any.
_NEXT_CALL_RE = re.compile(r"\n\s*TOOL:\s*\w+")


def _safe(fn: Callable[[str], str]) -> Callable[[str], str]:
    def wrapped(arg: str) -> str:
        try:
            return fn(arg)[:_MAX_OBSERVATION_CHARS]
        except Exception as exc:  # a flaky tool degrades the conversation, not crashes it
            return f"[tool error: {exc}]"
    return wrapped


@_safe
def _read(url: str) -> str:
    return reader.fetch_text(url)


@_safe
def _search(query: str) -> str:
    hits = search.web_search(query, k=5)
    if not hits:
        return "(no results)"
    return "\n".join(f"- {h.title} ({h.url}): {h.snippet}" for h in hits)


@_safe
def _physlib(source: str) -> str:
    result = physlib.verify(source)
    return result.summary() if result.ok else f"{result.summary()}\n{result.log}"


@_safe
def _pyexec(code: str) -> str:
    result = pyexec.run(code)
    if result is None:
        return "(no code provided)"
    return (f"ok={result.ok} returncode={result.returncode}\n"
           f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")


@_safe
def _paperqa(question: str) -> str:
    return paperqa.literature_review(question)


EXECUTORS: dict[str, Callable[[str], str]] = {
    "reader": _read,
    "web_search": _search,
    "physlib": _physlib,
    "pyexec": _pyexec,
    "paperqa": _paperqa,
}

_ARG_HINTS = {
    "reader": "a URL to fetch and read as plain text",
    "web_search": "a search query",
    "physlib": "Lean 4 (Physlib) source to verify",
    "pyexec": "Python source to run (stdout/stderr are returned)",
    "paperqa": "a natural-language research question - returns a citation-backed literature review",
}


def run_tool(name: str, arg: str) -> str:
    executor = EXECUTORS.get(name)
    if executor is None:
        return f"[unknown tool {name!r}]"
    return executor(arg)


def parse_tool_call(text: str, allowed: tuple[str, ...]) -> tuple[str, str, bool] | None:
    """Detect a `TOOL: <name>\\n<argument>` response. None if not a (permitted)
    call. The argument is truncated at the next `TOOL:`-prefixed line, if the
    model wrote one - the third element of the return tuple is True when that
    truncation happened, so the caller can tell the model it misbehaved."""
    m = _TOOL_CALL_RE.match(text.strip())
    if not m:
        return None
    name, rest = m.group(1), m.group(2)
    boundary = _NEXT_CALL_RE.search(rest)
    truncated = boundary is not None
    arg = (rest[:boundary.start()] if truncated else rest).strip()
    if name not in allowed or name not in EXECUTORS:
        return None
    return name, arg, truncated


def protocol_hint(tool_names: tuple[str, ...]) -> str:
    """Prompt text explaining the TOOL: protocol, scoped to the callable tools given."""
    callable_names = [t for t in tool_names if t in EXECUTORS]
    if not callable_names:
        return ""
    lines = [f"- {n}: argument is {_ARG_HINTS[n]}" for n in callable_names]
    return (
        "To use a tool, respond with ONLY:\nTOOL: <name>\n<argument>\n\n"
        "Available tools:\n" + "\n".join(lines) + "\n\n"
        f"You get up to {MAX_TOOL_TURNS} tool calls. Call EXACTLY ONE tool per "
        "response, then stop and wait: do not write more than one `TOOL:` line "
        "in a single response, and do not write your own `Observation:` or "
        "otherwise invent what the tool might return - the real observation "
        "will be given back to you before you continue. After each real "
        "observation, either call another tool the same way or give your "
        "final answer in the required output format (a response that does "
        "not start with `TOOL:`)."
    )
