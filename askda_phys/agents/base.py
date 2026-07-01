"""Agent base class.

Every agent in the plan shares the same five-part template (persona, objective,
context, tool guidance, output+evaluation). We capture that as data in
`AgentSpec` and let one `Agent` class render the prompt, call the model at the
right tier, parse a score if the agent reports one, and log the exchange.

Agents that need genuine tool-use loops (e.g. `leangrad` driving Lean/scipy,
`advisor` doing web search) override `act()`. The base `act()` is single-shot.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .. import models
from ..scoring import parse_score

if TYPE_CHECKING:  # avoid a hard import cycle with orchestration
    from .orchestration.run import Run


@dataclass(frozen=True)
class AgentSpec:
    name: str
    tier: str                      # "FAST" | "SMART" | "GENIUS"
    persona: str                   # role / persona block
    objective: str                 # what the agent must do
    context_template: str          # uses {named} placeholders filled at call time
    tool_guidance: str = ""        # human-readable; tool wiring lives in act()
    reports_score: bool = False    # whether to parse a trailing SCORE=
    tools: tuple[str, ...] = ()    # names of tools this agent may use


@dataclass
class AgentResult:
    agent: str
    text: str
    score: float | None = None
    meta: dict = field(default_factory=dict)


class Agent:
    def __init__(self, spec: AgentSpec):
        self.spec = spec

    # -- prompt construction ------------------------------------------------ #
    def system_prompt(self) -> str:
        return self.spec.persona.strip()

    def render_prompt(self, context: dict[str, str]) -> str:
        try:
            ctx = self.spec.context_template.format(**context)
        except KeyError as exc:
            raise KeyError(
                f"Agent {self.spec.name!r} context missing key {exc}"
            ) from exc
        parts = [self.spec.objective.strip(), "", ctx.strip()]
        if self.spec.tool_guidance:
            parts += ["", f"Tool guidance: {self.spec.tool_guidance.strip()}"]
        return "\n".join(parts).strip()

    # -- execution ---------------------------------------------------------- #
    def act(self, context: dict[str, str], run: "Run | None" = None,
            iteration: int | None = None) -> AgentResult:
        """Single-shot execution. Override for multi-step tool use."""
        prompt = self.render_prompt(context)
        system = self.system_prompt()
        text = models.call(self.spec.tier, prompt, system)
        score = parse_score(text) if self.spec.reports_score else None
        if run is not None:
            run.log(self.spec.name, prompt, text, iteration=iteration)
        return AgentResult(agent=self.spec.name, text=text, score=score)

    # convenience
    def __call__(self, context: dict[str, str], run: "Run | None" = None,
                 iteration: int | None = None) -> AgentResult:
        return self.act(context, run=run, iteration=iteration)
