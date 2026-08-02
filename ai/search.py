from __future__ import annotations

import time
from typing import Hashable

from .config import AIConfig
from .evaluator import Evaluator
from .models import Move, SearchStats
from .move_generator import MoveGenerator
from .rules_protocol import RulesEngine
from .transposition import Bound, TTEntry, TranspositionTable


class SearchTimeout(Exception):
    """Internal control flow; every caller uses apply/undo in try/finally."""


class SearchEngine:
    def __init__(
        self, rules: RulesEngine, config: AIConfig, generator: MoveGenerator,
        evaluator: Evaluator, table: TranspositionTable,
    ) -> None:
        self.rules, self.config = rules, config
        self.generator, self.evaluator, self.table = generator, evaluator, table
        self.stats, self.deadline, self.ai_player = SearchStats(), 0.0, 1

    def begin(self, deadline: float, ai_player: int) -> None:
        self.deadline, self.ai_player, self.stats = deadline, ai_player, SearchStats()

    def _check_time(self) -> None:
        if (
            self.stats.nodes % self.config.deadline_check_interval == 0
            and time.perf_counter() >= self.deadline
        ):
            raise SearchTimeout

    def _terminal_score(self, state: object, ply: int) -> int | None:
        result = self.rules.get_result(state)
        if not result.terminal:
            return None
        if result.winner is None:
            return 0
        value = self.config.mate_score - ply
        return value if result.winner == self.ai_player else -value

    def search_depth(self, state: object, depth: int) -> tuple[int, tuple[Move, ...]]:
        return self._minimax(
            state, depth, -self.config.mate_score, self.config.mate_score, 0
        )

    def _key(self, state: object, ply: int) -> tuple[Hashable, int, int]:
        # Ply is part of the key because terminal scores encode mate distance.
        return (self.rules.get_state_hash_data(state), self.ai_player, ply)

    def _ordered_moves(self, state: object, player: int, ply: int) -> list[Move]:
        moves = self.generator.candidates(state, player)
        tactical = self.rules.get_tactical_moves(state, player)
        legal_set = set(moves)
        ordered_tactical = (
            tactical.secure_wins + tactical.capture_wins
            + tactical.pending_win_breaks + tactical.immediate_loss_blocks
            + tactical.capture_win_defenses + tactical.captures
        )
        special: list[Move] = []
        seen: set[Move] = set()
        for move in ordered_tactical:
            if move in legal_set and move not in seen:
                special.append(move)
                seen.add(move)
        # Every engine-reported tactical move bypasses quiet candidate limiting.
        limit = self.config.candidate_limit(ply)
        quiet = [move for move in moves if move not in seen]
        return special + quiet[:limit]

    def _minimax(
        self, state: object, depth: int, alpha: int, beta: int, ply: int
    ) -> tuple[int, tuple[Move, ...]]:
        self.stats.nodes += 1
        self._check_time()
        terminal = self._terminal_score(state, ply)
        if terminal is not None:
            return terminal, ()
        if depth == 0:
            return self.evaluator.evaluate(state, self.ai_player), ()

        key, alpha_start, beta_start = self._key(state, ply), alpha, beta
        entry = self.table.get(key)
        if entry is not None and entry.depth >= depth:
            self.stats.cache_hits += 1
            if entry.bound == Bound.EXACT:
                return entry.score, entry.pv
            if entry.bound == Bound.LOWER:
                alpha = max(alpha, entry.score)
            else:
                beta = min(beta, entry.score)
            if alpha >= beta:
                return entry.score, entry.pv

        player = self.rules.get_current_player(state)
        maximizing = player == self.ai_player
        best = -self.config.mate_score if maximizing else self.config.mate_score
        best_move: Move | None = None
        best_child: tuple[Move, ...] = ()
        moves = self._ordered_moves(state, player, ply)
        if entry is not None and entry.best_move in moves:
            moves.remove(entry.best_move)  # type: ignore[arg-type]
            moves.insert(0, entry.best_move)  # type: ignore[arg-type]
        if not moves:
            return self.evaluator.evaluate(state, self.ai_player), ()

        for move in moves:
            token = self.rules.apply_move(state, move, player)
            try:
                score, child = self._minimax(state, depth - 1, alpha, beta, ply + 1)
            finally:
                self.rules.undo_move(state, token)
            if (
                (maximizing and score > best)
                or (not maximizing and score < best)
                or (score == best and (best_move is None or move < best_move))
            ):
                best, best_move, best_child = score, move, child
            if maximizing:
                alpha = max(alpha, best)
            else:
                beta = min(beta, best)
            # No sibling can beat an immediate terminal result at this ply.
            immediate_mate = self.config.mate_score - (ply + 1)
            if (maximizing and best == immediate_mate) or (
                not maximizing and best == -immediate_mate
            ):
                self.stats.cutoffs += 1
                break
            if alpha >= beta:
                self.stats.cutoffs += 1
                break

        bound = (
            Bound.UPPER if best <= alpha_start
            else Bound.LOWER if best >= beta_start
            else Bound.EXACT
        )
        pv = ((best_move,) + best_child) if best_move is not None else ()
        self.table.put(key, TTEntry(depth, best, bound, best_move, pv))
        return best, pv

    def plain_minimax(
        self, state: object, depth: int, ai_player: int
    ) -> tuple[int, tuple[Move, ...]]:
        """Reference implementation for tests and teaching, without pruning/cache."""
        self.ai_player = ai_player
        return self._plain_minimax(state, depth, 0)

    def _plain_minimax(
        self, state: object, depth: int, ply: int
    ) -> tuple[int, tuple[Move, ...]]:
        terminal = self._terminal_score(state, ply)
        if terminal is not None:
            return terminal, ()
        if depth == 0:
            return self.evaluator.evaluate(state, self.ai_player), ()
        player = self.rules.get_current_player(state)
        maximizing, best, best_pv = player == self.ai_player, None, ()
        for move in self.generator.candidates(state, player):
            token = self.rules.apply_move(state, move, player)
            try:
                score, pv = self._plain_minimax(state, depth - 1, ply + 1)
            finally:
                self.rules.undo_move(state, token)
            if best is None or (score > best if maximizing else score < best):
                best, best_pv = score, (move,) + pv
        return (
            (self.evaluator.evaluate(state, self.ai_player), ())
            if best is None else (best, best_pv)
        )
