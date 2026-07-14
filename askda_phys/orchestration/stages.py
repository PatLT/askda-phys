"""Staged, checkpointed execution of the discovery pipeline.

`discover()` (pipeline.py) runs the whole DAG for one seed in a single call.
The stages here let you run it in controlled, resumable chunks instead, so you
can process `n` seeds now and `n` more later without re-spending tokens on
what's already done:

  stage 0 (`run_stage0_ranking`): rank every unused seed, write the full
    ordered list to a JSON checkpoint (`config.RANKING_CHECKPOINT_PATH`).
  stage 1 (`run_stage1`): read that checkpoint, take the next `n` seeds not
    already present in the stage-1 checkpoint, run cafeteam -> panelone
    (advisor + internal/revtwo/bureaucrat) on each, append one JSON line per
    seed (`config.STAGE1_CHECKPOINT_PATH`) - the stored "advisor" entry is
    panelone's *best*-scoring attempt, with its reviews and total score, not
    just a single advisor call.
  stage 1, advisor-only (`run_stage1_advisor_only`): re-run just panelone -
    not cafeteam - for up to `n` existing entries with cafeteam.passed ==
    True, using their already-stored cafeteam output - no cafeteam
    re-attempt. Overwrites those entries in place (rewrites the whole
    checkpoint) rather than appending.

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
built yet; `run_stage1` stops after panelone.
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


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    """Rewrite the whole file (unlike the normal stage-1 append) - write to a
    temp file and atomically replace, so a crash mid-write can't leave a
    truncated/corrupted checkpoint."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(json.dumps(e) + "\n" for e in entries))
    tmp.replace(path)


def _already_processed(path: Path) -> set[str]:
    return {e["seed"] for e in _read_jsonl(path)}


def _panel_entry(panel) -> dict:
    """Serialize a panelone PanelResult's best attempt for the stage-1
    checkpoint: the winning proposal, each reviewer's score + text, and the
    total score - not the full all_attempts history."""
    best = panel.best
    return {
        "proposal": best.proposal,
        "grounded_constants": [p.name for p in best.grounded],
        "reviews": {
            "internal": {"score": best.internal_score, "text": best.internal_text},
            "revtwo": {"score": best.revtwo_score, "text": best.revtwo_text},
            "bureaucrat": {"score": best.bureaucrat_score, "text": best.bureaucrat_text},
        },
        "total_score": best.total_score,
        "attempts": panel.attempts,
    }


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
            panel = agents.panelone.run_panelone(
                cafe.analogy, cafe.novelty_text, cafe.credibility_text,
                run=run, verbosity=verbosity)
            entry["advisor"] = _panel_entry(panel)

        with checkpoint_path.open("a") as fh:
            fh.write(json.dumps(entry) + "\n")
        results.append(entry)

        if verbosity >= 2:
            verdict = "ACCEPT" if cafe.passed else "REJECT"
            advisor_status = "ran" if entry["advisor"] else "skipped"
            tqdm.write(f"{seed}: cafeteam={verdict} (total={cafe.total_score}, "
                      f"attempts={cafe.attempts}) advisor={advisor_status}")

    return results


def run_stage1_advisor_only(n: int, *,
                            checkpoint_path: Path = STAGE1_CHECKPOINT_PATH,
                            verbosity: int = 0) -> list[dict]:
    """Re-run just advisor - not cafeteam - for up to `n` entries in the
    stage-1 checkpoint that already have `cafeteam.passed == True`, using
    their already-stored cafeteam output (analogy/novelty/credibility text).
    No cafeteam re-attempt, so no new tokens spent on maniac/interpreter/
    sceptic, and no risk of cafeteam's stochastic output changing underneath
    you. Useful after changing advisor's prompt/logic and wanting to
    regenerate proposals without re-rolling the idea itself.

    Unlike `run_stage1`, this overwrites existing entries rather than adding
    new ones, so it rewrites the whole checkpoint file (see `_write_jsonl`)
    instead of appending. Doesn't touch `web` at all - no new seeding, no
    description backfill (already done when the entry was first created).
    """
    entries = _read_jsonl(checkpoint_path)
    eligible = [i for i, e in enumerate(entries) if e["cafeteam"]["passed"]][:n]

    updated = []
    for i in tqdm(eligible, desc="stage1 advisor-only", unit="seed",
                 disable=verbosity < 1):
        entry = entries[i]
        cafe = entry["cafeteam"]
        run = Run(seed_node=entry["seed"])
        panel = agents.panelone.run_panelone(
            cafe["analogy"], cafe["novelty_text"], cafe["credibility_text"],
            run=run, verbosity=verbosity)
        entry["advisor"] = _panel_entry(panel)
        entry["run_label"] = run.label
        updated.append(entry)

        if verbosity >= 2:
            tqdm.write(f"[{entry['seed']}] advisor re-run -> {run.label}")

    _write_jsonl(checkpoint_path, entries)
    return updated
