"""Physlib (Lean 4) verification tool.

Used by `leangrad` (to prove model soundness), `peer` (correctness checks) and
`critic` (reduction-to-known-solutions checks).

The value of the verifier-in-the-loop repair in `leangrad` is bounded entirely
by how informative this module's return is. So `verify` returns a *structured*
`LeanResult` - parsed errors, remaining `sorry`s, a rough open-goal count, and a
`progress` key - not just a pass/fail bit. That structure is the feedback signal
the repair loop climbs, and the progress key lets the loop keep the best partial
proof instead of the most recent attempt.

STATUS: the parser and result types are real and unit-tested. The `lake`
invocation runs only when ASKDA_PHYSLIB_PATH points at a built Physlib checkout
(leanprover-community/physlib - note the rename from PhysLean/HepLean); otherwise
`verify` returns a structured "not attempted" result so the loop degrades
gracefully to the numerical fallback.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# Set ASKDA_PHYSLIB_PATH to a built Physlib project to enable real verification.
PHYSLIB_PATH = os.environ.get("ASKDA_PHYSLIB_PATH")


@dataclass
class LeanError:
    line: int | None
    message: str


@dataclass
class LeanResult:
    ok: bool                         # elaborates with no errors AND no sorries
    log: str                         # raw compiler output
    compiles: bool = False           # elaborates (errors=0), even if sorries remain
    errors: list[LeanError] = field(default_factory=list)
    sorries: int = 0                 # `declaration uses 'sorry'` count
    open_goals: int = 0              # rough count of `unsolved goals`
    attempted: bool = True           # False when no toolchain was available

    @property
    def progress(self) -> tuple[int, int, int, int]:
        """Lexicographic key; larger is better. Lets the loop keep the best partial.

        (compiles?, fewer sorries, fewer open goals, fewer errors)
        """
        return (int(self.compiles), -self.sorries, -self.open_goals,
                -len(self.errors))

    def summary(self) -> str:
        if not self.attempted:
            return "not attempted (no Lean toolchain configured)"
        if self.ok:
            return "verified"
        bits = [f"{len(self.errors)} error(s)"]
        if self.sorries:
            bits.append(f"{self.sorries} sorry")
        if self.open_goals:
            bits.append(f"{self.open_goals} open goal(s)")
        return ", ".join(bits)


# --------------------------------------------------------------------------- #
# Output parsing (real; unit-tested)
# --------------------------------------------------------------------------- #
_DIAG_RE = re.compile(r":(\d+):\d+:\s*(error|warning):\s*(.*)", re.IGNORECASE)
_SORRY_RE = re.compile(r"declaration uses ['\"]sorry['\"]", re.IGNORECASE)
_GOALS_RE = re.compile(r"unsolved goals", re.IGNORECASE)


def parse_lean_output(log: str) -> LeanResult:
    errors: list[LeanError] = []
    for m in _DIAG_RE.finditer(log or ""):
        line, kind, msg = int(m.group(1)), m.group(2).lower(), m.group(3).strip()
        if kind == "error":
            errors.append(LeanError(line=line, message=msg))
    sorries = len(_SORRY_RE.findall(log or ""))
    open_goals = len(_GOALS_RE.findall(log or ""))
    compiles = len(errors) == 0
    ok = compiles and sorries == 0
    return LeanResult(ok=ok, log=log, compiles=compiles, errors=errors,
                      sorries=sorries, open_goals=open_goals)


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #
def verify(lean_source: str, *, timeout: float = 600.0) -> LeanResult:
    if not PHYSLIB_PATH:
        return LeanResult(
            ok=False, compiles=False, attempted=False,
            log=("ASKDA_PHYSLIB_PATH unset; skipping Lean verification. "
                 "Set it to a built Physlib checkout to enable proofs."),
        )
    project = Path(PHYSLIB_PATH)
    scratch = project / ".askda_scratch"
    scratch.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".lean", dir=scratch,
                                     delete=False) as fh:
        fh.write(lean_source)
        src_path = Path(fh.name)
    try:
        proc = subprocess.run(
            ["lake", "env", "lean", str(src_path)],
            cwd=project, capture_output=True, text=True, timeout=timeout,
        )
        log = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return parse_lean_output(log)
    except subprocess.TimeoutExpired:
        return LeanResult(ok=False, compiles=False, log="lean: timeout")
    except FileNotFoundError:
        return LeanResult(ok=False, compiles=False, attempted=False,
                          log="`lake` not found on PATH.")
    finally:
        src_path.unlink(missing_ok=True)
