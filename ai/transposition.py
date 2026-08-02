"""Bounded transposition table."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Hashable

from .models import Move


class Bound(IntEnum):
    EXACT = 0
    LOWER = 1
    UPPER = 2


@dataclass(slots=True)
class TTEntry:
    depth: int
    score: int
    bound: Bound
    best_move: Move | None
    pv: tuple[Move, ...]


class TranspositionTable:
    def __init__(self, capacity: int) -> None:
        self.capacity = max(1, capacity)
        self._items: dict[Hashable, TTEntry] = {}

    def get(self, key: Hashable) -> TTEntry | None:
        return self._items.get(key)

    def put(self, key: Hashable, entry: TTEntry) -> None:
        old = self._items.get(key)
        if old is not None and old.depth > entry.depth:
            return
        if len(self._items) >= self.capacity and key not in self._items:
            # Dict insertion order gives a cheap bounded FIFO replacement policy.
            self._items.pop(next(iter(self._items)))
        self._items[key] = entry

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)
