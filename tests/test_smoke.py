"""Smoke tests: the package imports and the pipeline runs end-to-end offline."""
from __future__ import annotations

from pathlib import Path

from askda_phys import models
from askda_phys.knowledge import KnowledgeWeb
from askda_phys.orchestration.pipeline import discover
from askda_phys.orchestration.run import Run
from askda_phys.scoring import gate, parse_score


def test_parse_score():
    assert parse_score("blah\nSCORE=4") == 4.0
    assert parse_score("SCORE=2 then SCORE=5") == 5.0   # last wins
    assert parse_score("no score here") is None


def test_gate():
    assert gate([4.0, 3.0], 3.0) is True
    assert gate([2.0, 3.0], 3.0) is False
    assert gate([None, None], 3.0) is False


def _tiny_web() -> KnowledgeWeb:
    web = KnowledgeWeb()
    web.add_node("Impermanence", kind="MEME", role="PHILOSOPHY",
                 description="Nothing persists; all is process.")
    web.add_node("Thermalisation", kind="MEME", role="APPLICATION",
                 description="Approach to equilibrium.")
    web.add_edge("Impermanence", "Thermalisation", strength="STRONG")
    return web


def test_pipeline_runs_offline(tmp_path: Path):
    models.use_mock()
    web = _tiny_web()
    run = Run(runs_dir=tmp_path / "runs", seed_node="Impermanence")
    res = discover(web, "Impermanence", run=run)
    assert res.strength in {"FAILED", "WEAK", "STRONG"}
    assert (run.dir / "decision.json").exists()
    # the seed should now be marked as used
    assert run.label in web.g.nodes["Impermanence"]["seeded_runs"]
