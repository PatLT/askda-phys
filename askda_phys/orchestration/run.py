"""Run context.

A run gets a sequential, git-stamped label (e.g. `001-1a2b3c4`), a directory
under RUNS_DIR, and a logger that dumps every agent prompt/response so a run is
fully reconstructible.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ..config import RUNS_DIR


def _git_checkpoint() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip() or "nogit"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "nogit"


def _next_index(runs_dir: Path) -> int:
    runs_dir.mkdir(parents=True, exist_ok=True)
    existing = [p.name for p in runs_dir.iterdir() if p.is_dir()]
    indices = []
    for name in existing:
        head = name.split("-", 1)[0]
        if head.isdigit():
            indices.append(int(head))
    return (max(indices) + 1) if indices else 1


class Run:
    def __init__(self, runs_dir: Path | None = None, seed_node: str | None = None):
        self.runs_dir = runs_dir or RUNS_DIR
        idx = _next_index(self.runs_dir)
        self.label = f"{idx:03d}-{_git_checkpoint()}"
        self.dir = self.runs_dir / self.label
        self.dir.mkdir(parents=True, exist_ok=True)
        self.seed_node = seed_node
        self._step = 0
        self.events: list[dict] = []
        self._write_meta()

    def _write_meta(self) -> None:
        (self.dir / "run.json").write_text(json.dumps({
            "label": self.label,
            "seed_node": self.seed_node,
            "started": datetime.now(timezone.utc).isoformat(),
        }, indent=2))

    def log(self, agent: str, prompt: str, response: str,
            iteration: int | None = None) -> None:
        self._step += 1
        itr = "" if iteration is None else f"_iter{iteration}"
        stem = f"{self._step:02d}_{agent}{itr}"
        (self.dir / f"{stem}.prompt.txt").write_text(prompt)
        (self.dir / f"{stem}.response.txt").write_text(response)
        self.events.append({"step": self._step, "agent": agent,
                            "iteration": iteration, "stem": stem})

    def record(self, name: str, payload: dict) -> None:
        """Dump a structured artefact (e.g. the final decision summary)."""
        (self.dir / f"{name}.json").write_text(json.dumps(payload, indent=2))
