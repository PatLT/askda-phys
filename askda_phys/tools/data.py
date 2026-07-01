"""Grounded physical data (used by advisor / supervisor, read by peer).

Empirical grounding, done the trustworthy way: instead of scraping numbers out
of arbitrary web pages (unstructured, unciteable, easy for the model to misread),
we resolve *named* physical constants against CODATA via `scipy.constants`. Every
returned value carries its unit, uncertainty, and source, so it is unit-safe and
citeable, and so `peer` can score accuracy against a real reference rather than
its own memory.

Mechanism: proposal-writing agents emit placeholders of the form
`{{const: <standard name>}}` wherever they need a constant. `ground_text` swaps
each for the exact CODATA value and collects the `DataPoint`s. Anything that is
NOT a standard constant stays as the model's own order-of-magnitude estimate
(the deliberate fallback) - grounding never invents a value it cannot source.

Only fundamental constants are wired here. Adding a domain source (PDG,
astroquery, NIST, Materials Project) means adding a resolver with the same
`DataPoint` return; `ground_text`/`format_references` need no changes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_PLACEHOLDER = re.compile(r"\{\{\s*const:\s*(.+?)\s*\}\}", re.IGNORECASE)


@dataclass
class DataPoint:
    name: str
    value: float
    unit: str
    uncertainty: float
    source: str

    def inline(self) -> str:
        s = f"{self.value:g}"
        if self.unit:
            s += f" {self.unit}"
        if self.uncertainty:
            s += f" (\u00b1{self.uncertainty:g})"
        return f"{s} [{self.source}]"

    def as_dict(self) -> dict:
        return {"name": self.name, "value": self.value, "unit": self.unit,
                "uncertainty": self.uncertainty, "source": self.source}


# --------------------------------------------------------------------------- #
# CODATA lookup (scipy.constants)
# --------------------------------------------------------------------------- #
def _scipy():
    try:
        import scipy.constants as sc  # type: ignore
        return sc
    except ImportError:
        return None


def search_constants(query: str) -> list[str]:
    """Return CODATA constant names matching `query` (substring, case-insensitive)."""
    sc = _scipy()
    if sc is None:
        return []
    try:
        return list(sc.find(query))
    except Exception:
        return []


def lookup_constant(name: str) -> DataPoint | None:
    """Resolve a CODATA constant by exact name, else best substring match."""
    sc = _scipy()
    if sc is None:
        return None
    key = name if name in sc.physical_constants else None
    if key is None:
        hits = search_constants(name)
        key = hits[0] if hits else None
    if key is None:
        return None
    value, unit, uncertainty = sc.physical_constants[key]
    return DataPoint(name=key, value=float(value), unit=unit,
                     uncertainty=float(uncertainty),
                     source="CODATA via scipy.constants")


# --------------------------------------------------------------------------- #
# Text grounding
# --------------------------------------------------------------------------- #
def ground_text(text: str) -> tuple[str, list[DataPoint]]:
    """Replace `{{const: name}}` placeholders with CODATA values.

    Returns the grounded text and the list of resolved DataPoints. Unresolvable
    placeholders are marked `(ungrounded)` and left for the reviewer to notice;
    non-placeholder order-of-magnitude estimates pass through untouched.
    """
    points: list[DataPoint] = []

    def _repl(m: re.Match) -> str:
        name = m.group(1).strip()
        dp = lookup_constant(name)
        if dp is None:
            return f"{name} (ungrounded)"
        points.append(dp)
        return dp.inline()

    return _PLACEHOLDER.sub(_repl, text or ""), points


def format_references(points: list[DataPoint]) -> str:
    if not points:
        return "(no grounded reference values)"
    return "\n".join(f"- {p.name} = {p.inline()}" for p in points)
