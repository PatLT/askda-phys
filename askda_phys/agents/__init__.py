"""Agent registry. Each module exposes `agent` (an Agent instance) and `SPEC`."""
from __future__ import annotations

from . import (
    advisor,
    archivist,
    interpreter,
    maniac,
    memeticist,
    sceptic,
    supervisor,
)
from . import pubteam

__all__ = [
    "maniac",
    "interpreter",
    "sceptic",
    "advisor",
    "supervisor",
    "memeticist",
    "archivist",
    "pubteam",
]
