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
export ANTHROPIC_API_KEY=sk-ant-...      # required for the default (API) backend
```

`networkx` and `anthropic` are the hard dependencies. `httpx` (Ollama + page
reading) and `scipy`/`numpy` (numerical fallback) are optional extras.

## Model backends

All three tiers default to the **Anthropic API**:

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

# 1. build + save the initial web of knowledge (page-link fetch is stubbed)
python -m askda_phys.cli build-web

# 2. (after a memeticist pass labels nodes) rank unused memetic seeds
python -m askda_phys.cli rank

# 3. run one discovery pass - offline, no model server needed:
python -m askda_phys.cli run --mock
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
    maniac, interpreter, sceptic, advisor, supervisor, memeticist, archivist
    pubteam/           leangrad + peer + critic, plus the team runner
  knowledge/
    web.py             KnowledgeWeb (networkx wrapper + persistence)
    build.py           initial-web construction from seed pages
    ranking.py         centrality-based seed scoring
  tools/               search, reader, physlib (Lean), pyexec (scipy)
  orchestration/
    run.py             git-stamped run label, output dir, prompt/response logging
    pipeline.py        the full discovery DAG (two gates + bounded re-iteration)
  cli.py
```

## Component status

| Component | State | Notes |
|---|---|---|
| Agent base / spec / prompts | ✅ working | maniac, interpreter, sceptic, advisor, leangrad, peer, critic carry their real prompts |
| memeticist / supervisor / archivist | 🟡 draft | prompts marked TBD in the plan; first-pass specs included |
| Tiered model dispatch | ✅ working | Anthropic API (default) + Ollama + Mock; switch via `use_*()` |
| KnowledgeWeb + persistence | ✅ working | MEME/COMPLEX, PHILOSOPHY/APPLICATION, STRONG/WEAK/FAILED |
| Seed ranking | ✅ working | implements the distance−centrality scoring from the plan |
| Run context + logging | ✅ working | `NNN-{gitsha}` labels, per-agent prompt/response dumps |
| Pipeline (gates + re-iteration) | ✅ working | runs offline with the mock model |
| Initial-web page-link fetch | 🟥 stub | `knowledge/build.fetch_links` returns []; wire to reader/MediaWiki |
| web_search tool | 🟥 stub | wire to a search API |
| page reader tool | 🟡 minimal | naive HTML->text; swap in trafilatura/readability |
| Physlib (Lean) verify | 🟡 real parser + lake call | structured errors/sorries/progress; runs `lake` when `ASKDA_PHYSLIB_PATH` is set, graceful no-op otherwise |
| leangrad repair loop | ✅ working | linear verifier-in-the-loop: structured errors fed back, keeps best partial by `progress`, numerical fallback on exhaustion |
| CODATA grounding | ✅ working | advisor/supervisor emit `{{const: ...}}`, resolved via `scipy.constants`, carried to `peer`; OOM estimate as fallback |
| pyexec (scipy) | 🟡 minimal | bare subprocess; sandbox before trusting model code |

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

1. Replace `knowledge/build.fetch_links` with real link extraction and run the
   `memeticist` pass to populate MEME/PHILOSOPHY/APPLICATION labels.
2. Point `ASKDA_PHYSLIB_PATH` at a built Physlib checkout to activate real Lean
   verification (the parser, `lake` call, and repair loop are already wired; the
   toolchain is the remaining external dependency).
3. Finalise the three draft agents (memeticist, supervisor, archivist).
