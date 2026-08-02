from __future__ import annotations

from dataclasses import dataclass

Move = tuple[int, int]


@dataclass(slots=True, frozen=True)
class GameResult:
    """Rule-engine verdict. A non-terminal position has ``terminal=False``."""

    terminal: bool = False
    winner: int | None = None
    reason: str = ""


@dataclass(slots=True)
class SearchResult:
    move: Move | None
    score: int
    completed_depth: int
    nodes: int
    elapsed_ms: float
    principal_variation: tuple[Move, ...]
    cache_hits: int
    cutoffs: int


@dataclass(slots=True)
class SearchStats:
    nodes: int = 0
    cache_hits: int = 0
    cutoffs: int = 0


@dataclass(slots=True, frozen=True)
class PlayedMove:
    move: Move
    player: int
    captured_stones: int = 0
    created_threat: bool = False


@dataclass(slots=True, frozen=True)
class TacticalMoves:
    """Rule-aware moves supplied by the engine; all fields bypass quiet limits."""

    secure_wins: tuple[Move, ...] = ()
    capture_wins: tuple[Move, ...] = ()
    pending_win_breaks: tuple[Move, ...] = ()
    immediate_loss_blocks: tuple[Move, ...] = ()
    capture_win_defenses: tuple[Move, ...] = ()
    captures: tuple[Move, ...] = ()

    def forced(self) -> tuple[Move, ...]:
        return (
            self.secure_wins + self.capture_wins + self.pending_win_breaks
            + self.immediate_loss_blocks + self.capture_win_defenses
        )
