"""Staged, checkpointed execution of the discovery pipeline.

`discover()` (pipeline.py) runs the whole DAG for one seed in a single call.
The stages here let you run it in controlled, resumable chunks instead, so you
can process `n` seeds now and `n` more later without re-spending tokens on
what's already done:

  stage 0 (`run_stage0_ranking`): rank every unused seed, write the full
    ordered list to a JSON checkpoint (`config.RANKING_CHECKPOINT_PATH`).
  stage 1 (`run_stage1`): read that checkpoint, take the next `n` seeds not
    already present in the stage-1 checkpoint, run cafeteam -> advisor on
    each, append one JSON line per seed (`config.STAGE1_CHECKPOINT_PATH`).

Seed selection for stage 1 is driven purely by the stage-0 checkpoint file - a
specific, reproducible ranking snapshot (ranking is sensitive to tunables like
the SEMANTIC-edge frequency cutoff, so "top n" depends on exactly how that
snapshot was produced) - plus stage 1's own checkpoint (to avoid reprocessing
a seed already recorded there). It does NOT re-filter live against
`web.unused_seed_nodes()`. `web.mark_seeded()` is still called and saved for
every processed seed - so it's recorded, and so a *later* stage-0 re-run
naturally excludes it via the existing `unused_seed_nodes()` filter - it just
isn't used to gate stage 1's own selection within a run.

Later stages (pubteam pass 1, supervisor, pubteam pass 2, archive) aren't
built yet; `run_stage1` stops after advisor.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from tqdm import tqdm

from .. import agents
from ..config import RANKING_CHECKPOINT_PATH, STAGE1_CHECKPOINT_PATH, WEB_PATH
from ..knowledge.descriptions import ensure_description
from ..knowledge.ranking import rank_seeds
from ..knowledge.web import KnowledgeWeb
from .run import Run


def run_stage0_ranking(web: KnowledgeWeb, path: Path = RANKING_CHECKPOINT_PATH,
                       **rank_kwargs) -> list[dict]:
    """Rank every unused seed and write the full ordered list to `path`
    (overwriting any previous snapshot). Returns the same rows written."""
    ranked = rank_seeds(web, **rank_kwargs)
    rows = [asdict(s) for s in ranked]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2))
    return rows


def _load_ranking(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"No ranking checkpoint at {path}; run stage 0 first.")
    return json.loads(path.read_text())


def _already_processed(path: Path) -> set[str]:
    if not path.exists():
        return set()
    seeds = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            seeds.add(json.loads(line)["seed"])
    return seeds


def run_stage1(web: KnowledgeWeb, n: int, *,
              ranking_path: Path = RANKING_CHECKPOINT_PATH,
              checkpoint_path: Path = STAGE1_CHECKPOINT_PATH,
              verbosity: int = 0) -> list[dict]:
    """Run cafeteam -> advisor on the next `n` not-yet-processed seeds from
    the stage-0 ranking checkpoint, appending one result line per seed to
    `checkpoint_path`. Returns the entries written this call (not the whole
    accumulated file)."""
    ranking = _load_ranking(ranking_path)
    done = _already_processed(checkpoint_path)
    candidates = [row for row in ranking if row["node"] not in done][:n]
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    for row in tqdm(candidates, desc="stage1", unit="seed", disable=verbosity < 1):
        seed = row["node"]
        description = ensure_description(web, seed)
        run = Run(seed_node=seed)
        web.mark_seeded(seed, run.label)
        web.save(WEB_PATH)  # single save: captures both the backfilled description and mark_seeded

        cafe = agents.cafeteam.run_cafeteam(seed, description, run=run, verbosity=verbosity)

        entry = {
            "seed": seed,
            "rank_score": row["score"],
            "run_label": run.label,
            "cafeteam": {
                "passed": cafe.passed,
                "attempts": cafe.attempts,
                "total_score": cafe.total_score,
                "analogy": cafe.analogy,
                "novelty_score": cafe.novelty_score,
                "novelty_text": cafe.novelty_text,
                "credibility_score": cafe.credibility_score,
                "credibility_text": cafe.credibility_text,
            },
            "advisor": None,
        }

        if cafe.passed:
            advisor_out = agents.advisor.agent({
                "maniac": cafe.analogy,
                "interpreter": cafe.novelty_text,
                "sceptic": cafe.credibility_text,
            }, run=run)
            grounded = list(advisor_out.meta.get("grounded", []))
            entry["advisor"] = {
                "proposal": advisor_out.text,
                "grounded_constants": [p.name for p in grounded],
            }

        with checkpoint_path.open("a") as fh:
            fh.write(json.dumps(entry) + "\n")
        results.append(entry)

        if verbosity >= 2:
            verdict = "ACCEPT" if cafe.passed else "REJECT"
            advisor_status = "ran" if entry["advisor"] else "skipped"
            tqdm.write(f"{seed}: cafeteam={verdict} (total={cafe.total_score}, "
                      f"attempts={cafe.attempts}) advisor={advisor_status}")

    return results
