"""Tests for the two new features: CODATA grounding and structured Lean parsing."""
from __future__ import annotations

from askda_phys.tools import data, physlib


# --- CODATA grounding ------------------------------------------------------- #
def test_lookup_known_constant():
    dp = data.lookup_constant("speed of light in vacuum")
    assert dp is not None
    assert round(dp.value) == 299792458
    assert "m" in dp.unit
    assert "CODATA" in dp.source


def test_lookup_fuzzy_and_missing():
    assert data.lookup_constant("Newtonian constant of gravitation") is not None
    assert data.lookup_constant("definitely not a constant xyzzy") is None


def test_ground_text_substitutes_and_collects():
    text = ("The bound involves {{const: speed of light in vacuum}} and a "
            "model-specific scale of ~10^5.")
    grounded, points = data.ground_text(text)
    assert "{{const:" not in grounded          # placeholder replaced
    assert "~10^5" in grounded                 # OOM fallback untouched
    assert len(points) == 1
    assert points[0].name == "speed of light in vacuum"


def test_ground_text_unresolved_is_marked():
    grounded, points = data.ground_text("value {{const: not real quux}} here")
    assert "(ungrounded)" in grounded
    assert points == []


# --- Lean output parsing ---------------------------------------------------- #
def test_parse_clean_compile():
    r = physlib.parse_lean_output("")           # no diagnostics
    assert r.compiles and r.ok
    assert r.errors == [] and r.sorries == 0


def test_parse_errors_and_sorry():
    log = (
        "/p/File.lean:12:5: error: unknown identifier 'foo'\n"
        "/p/File.lean:20:0: error: unsolved goals\n"
        "warning: declaration uses 'sorry'\n"
    )
    r = physlib.parse_lean_output(log)
    assert len(r.errors) == 2
    assert r.sorries == 1
    assert r.open_goals == 1
    assert not r.compiles and not r.ok


def test_progress_prefers_compiling_partial():
    broken = physlib.parse_lean_output("/p/F.lean:1:0: error: boom")
    with_sorry = physlib.parse_lean_output("warning: declaration uses 'sorry'")
    # a file that elaborates with a sorry beats one that does not compile
    assert with_sorry.progress > broken.progress


def test_verify_without_toolchain_is_graceful():
    r = physlib.verify("theorem t : True := trivial")
    assert r.attempted is False
    assert r.ok is False
