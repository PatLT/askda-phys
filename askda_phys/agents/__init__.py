"""Agent registry. Each module exposes `agent` (an Agent instance) and `SPEC`."""
from __future__ import annotations

from . import (
    advisor,
    archivist,
    memeticist,
    supervisor,
)
from . import cafeteam, pubteam

__all__ = [
    "advisor",
    "supervisor",
    "memeticist",
    "archivist",
    "cafeteam",
    "pubteam",
]
