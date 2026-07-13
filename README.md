# ASKDA-Phys

**Agents for knowledge Systemisation and Discovery-by-Analogy in Physics.**

A pipeline of tiered LLM agents that draws analogies from philosophy to physics,
reviews them for novelty and credibility, attempts to formalise the survivors in
Lean 4 (Physlib), and records the outcomes in a growing *web of knowledge*.

This repository is a **scaffold**: the orchestration spine (agents, tiered model
dispatch, knowledge graph, run logging, gates, pipeline) is functional and runs
end-to-end with an offline mock model. The model-dependent and external pieces
are stubbed behind real interfaces (see the status table).

## Install

```bash
pip install -e ".[http,numeric,dev]"
export DEEPSEEK_API_KEY=sk-...      # required for the default (API) backend
```

`networkx` and `anthropic` are the hard dependencies. `httpx` (Ollama + page
reading) and `scipy`/`numpy` (numerical fallback) are optional extras.

## Model backends

All three tiers default to the **Deepseek API**:

| Tier | Model | Used by |
|---|---|---|
| FAST | `deepseek-v4-flash` | memeticist, archivist |
| SMART | `deepseek-v4-pro` | interpreter, sceptic, advisor, supervisor, peer, critic |
| GENIUS | `deepseek-v4-pro` | maniac, leangrad |

The Anthropic API might be preferred:

| Tier | Model | Used by |
|---|---|---|
| FAST | `claude-haiku-4-5-20251001` | memeticist, archivist |
| SMART | `claude-sonnet-4-6` | interpreter, sceptic, advisor, supervisor, peer, critic |
| GENIUS | `claude-opus-4-8` | maniac, leangrad |

Opus 4.8 is the strongest model with open API access; the Mythos-class tier
(Fable 5 / Mythos 5) sits above it but its API access is currently suspended —
swap GENIUS to `claude-fable-5` in `config.py` if your account has access.

Switch backends at runtime: `models.use_anthropic()` (default),
`models.use_ollama()` (local), `models.use_mock()` (offline tests). Per-tier
model IDs, temperatures, and `max_tokens` live in `config.py`. To add another
provider, write a client with the same `.generate` signature and call
`models.register_client(...)`.

## Quickstart

```bash
# 0. Run tests - 11 tests should pass
python -m pytest -q

# 1. build + save the initial web of knowledge
python -m askda_phys.cli build-web

# 2. (after a memeticist pass labels nodes) rank seeds - persists the FULL
#    ordered list to .askda/checkpoints/ranking.json, prints the top --top
python -m askda_phys.cli rank

# 3a. run one discovery pass unstaged, start to finish - offline, no model
#     server needed:
python -m askda_phys.cli run --mock

# 3b. ...or run it staged, to control token spend: cafeteam -> advisor only,
#     on the next --n not-yet-processed seeds from the ranking checkpoint,
#     appended to .askda/checkpoints/stage1.jsonl (later stages: TODO)
python -m askda_phys.cli stage1 --n 10 --mock
```

In code:

```python
from askda_phys import models, KnowledgeWeb, discover
# default backend is the Anthropic API (needs ANTHROPIC_API_KEY);
# models.use_mock() for offline, models.use_ollama() for local models
web = KnowledgeWeb.load(".askda/web.json")
result = discover(web, "Impermanence") # one full pipeline pass
```

## Layout

```
askda_phys/
  config.py            model tiers, thresholds, paths, seed pages
  models.py            tier dispatch + Ollama / Mock clients
  scoring.py           SCORE= parsing and gate logic
  agents/
    base.py            Agent + AgentSpec (the shared 5-part template)
    tooling.py         TOOL: call/observe loop + executors (reader, web_search, physlib, pyexec)
    advisor, supervisor, memeticist, archivist
    cafeteam/          maniac + interpreter + sceptic, plus the team runner (reattempt loop)
    pubteam/           leangrad + peer + critic, plus the team runner (reattempt loop)
  knowledge/
    web.py             KnowledgeWeb (networkx wrapper + persistence)
    build.py           initial-web construction from seed pages
    ranking.py         centrality-based seed scoring
  tools/               search, reader, physlib (Lean), pyexec (scipy)
  orchestration/
    run.py             git-stamped run label, output dir, prompt/response logging
    pipeline.py        the full discovery DAG (two gates + bounded re-iteration)
    stages.py          checkpointed stage 0 (rank) / stage 1 (cafeteam -> advisor)
  cli.py
```

## Component status

| Component | State | Notes |
|---|---|---|
| Agent base / spec / prompts | ✅ working | all agents (maniac, interpreter, sceptic, advisor, supervisor, memeticist, archivist, leangrad, peer, critic) carry their real prompts |
| cafeteam / pubteam reattempt loops | ✅ working | `run_cafeteam`/`run_pubteam` re-run their idea agent (maniac / leangrad) up to `N_MANIAC_REATTEMPTS`/`N_LEANGRAD_REATTEMPTS` (default 2) on a REATTEMPT verdict, concatenating each round's reviewer reports back into the idea agent's context; see `scoring.reattempt_decision` for the ACCEPT/REATTEMPT/REJECT rule on summed reviewer scores |
| Web-of-knowledge traversal (memeticist pass) | ✅ working | `knowledge.trawl_web` runs a cheap classify call over every unlabelled node (7 roles: PHILOSOPHY_CONCEPT/PHILOSOPHY_SCHOOL/PHILOSOPHER/SCIENCE_CONCEPT/SCIENTIST/PHENOMENON/OTHER), then the heavier expand+split call only over COMPLEX nodes whose role can source a seed (PHILOSOPHY_CONCEPT/PHILOSOPHY_SCHOOL/PHILOSOPHER); wired to `cli.py label-web` |
| Tiered model dispatch | ✅ working | Deepseek API (default) + Anthropic API + Ollama + Mock; switch via `use_*()` |
| KnowledgeWeb + persistence | ✅ working | MEME/COMPLEX, 7-role vocabulary (`agents.memeticist.ALL_ROLES`), STRONG/WEAK/FAILED |
| Seed ranking | ✅ working | implements the distance−centrality scoring from the plan |
| Staged / checkpointed pipeline | ✅ working (stage 0-1) | `orchestration/stages.py`: stage 0 ranks + persists the full ordered list (`.askda/checkpoints/ranking.json`, overwritten each run); stage 1 runs cafeteam->advisor on the next `n` seeds not yet in `.askda/checkpoints/stage1.jsonl` (append-only), so a batch is resumable across sessions without re-spending tokens. Seed selection reads only the checkpoint files, not live `web.json` state; `web.mark_seeded()` is still recorded for every processed seed. Later stages (pubteam, supervisor, archive) not yet built |
| Run context + logging | ✅ working | `NNN-{gitsha}` labels, per-agent prompt/response dumps |
| Pipeline (gates + re-iteration) | ✅ working | runs offline with the mock model; supervisor/archivist now get the actual peer/critic review text and a real field label instead of placeholders |
| Agent tool-call loop | ✅ working | `agents/tooling.py`: a `TOOL: <name>\n<arg>` wire protocol, opt-in via `AgentSpec.tool_loop`; wired into memeticist's expand step, advisor, supervisor, peer, and critic (bounded to `MAX_TOOL_TURNS`); `leangrad` keeps its own deterministic verifier-in-the-loop instead |
| Node description backfill | ✅ working | `knowledge/descriptions.py`: crawl-only nodes start with `description=""` (only `source_url` known at crawl time), leaving `maniac` with almost no context; `ensure_description` lazily pulls the first substantial `<p>` off `source_url` (`reader.fetch_first_paragraph`, no model call) the moment a seed is used, and persists it onto the node so it's fetched once |
| Initial-web page-link fetch | 🟡 minimal | `knowledge/build.fetch_links` performs a simple scrape of webpage for links to valid wiki pages |
| web_search tool | 🟡 minimal | basic search via duckduckgo API; now actually callable by advisor/supervisor/memeticist-expand via the tool-call loop |
| page reader tool | 🟡 minimal | naive HTML->text; swap in trafilatura/readability; now actually callable by memeticist-expand |
| Physlib (Lean) verify | 🟡 real parser + lake call | structured errors/sorries/progress; runs `lake` when `ASKDA_PHYSLIB_PATH` is set, graceful no-op otherwise; now also callable live by peer/critic (in addition to leangrad's own verifier loop) |
| leangrad repair loop | ✅ working | linear verifier-in-the-loop: structured errors fed back, keeps best partial by `progress`, numerical fallback on exhaustion; its verdict is now also summarised into peer/critic's own context |
| CODATA grounding | ✅ working | advisor/supervisor emit `{{const: ...}}`, resolved via `scipy.constants`, carried to `peer`; OOM estimate as fallback |
| pyexec (scipy) | 🟡 minimal | bare subprocess; sandbox before trusting model code; now also callable live via the tool-call loop |

## Notes

- **Physlib** PhysLean,
  formerly HepLean, was renamed and merged with Lean-QuantumInfo into
  **Physlib** at `leanprover-community/physlib`. Point your checkout there. A
  *separate* "PhysLib" (from the Lean4PHYS project, with the LeanPhysBench
  benchmark) is the more LLM-oriented one and is worth studying for the
  `leangrad`/`peer`/`critic` tooling.
- **`leangrad` is the load-bearing risk.** Autonomous Lean formalisation of
  research-level physics is currently weak. On *college-level* LeanPhysBench,
  the best frontier model scored ~35% and a dedicated prover ~16%; local models
  will be worse. The pipeline therefore treats Lean verification as an optional
  layer and keeps the scipy numerical path as the primary fallback.
- **Ollama**; it only runs models. The `tools/` layer executes
  search / page reading / Lean / Python in-process and feeds results back into
  the next prompt.

## Next steps (suggested order)

1. Point `ASKDA_PHYSLIB_PATH` at a built Physlib checkout to activate real Lean
   verification (the parser, `lake` call, and repair loop are already wired; the
   toolchain is the remaining external dependency).
2. Harden `pyexec` (sandbox before trusting model-generated code) and swap the
   naive HTML->text page reader for trafilatura/readability.
