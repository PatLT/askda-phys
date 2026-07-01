"""Python (scipy) execution tool - the numerical fallback for `leangrad`.

Runs model-generated Python in a subprocess with a timeout and captures stdout.
This executes untrusted, model-generated code: in any real deployment run it in
a proper sandbox (container / nsjail / restricted user), not bare subprocess.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExecResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int


def run(code: str | None, *, timeout: float = 120.0) -> ExecResult | None:
    if not code:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "solve.py"
        script.write_text(code)
        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True, text=True, timeout=timeout, cwd=tmp,
            )
        except subprocess.TimeoutExpired as exc:
            return ExecResult(False, exc.stdout or "", "timeout", -1)
        return ExecResult(proc.returncode == 0, proc.stdout, proc.stderr,
                          proc.returncode)
