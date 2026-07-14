"""Agent registry. Each module exposes `agent` (an Agent instance) and `SPEC`."""
from __future__ import annotations

from . import (
    archivist,
    memeticist,
    supervisor,
)
from . import cafeteam, panelone, pubteam

__all__ = [
    "supervisor",
    "memeticist",
    "archivist",
    "cafeteam",
    "panelone",
    "pubteam",
]
