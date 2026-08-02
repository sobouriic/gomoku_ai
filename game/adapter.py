from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Hashable

from .gomuku_backend import BLACK, EMPTY, WHITE, GomokuGame, MoveResult
from ai import GameResult, Move, PlayedMove, TacticalMoves


@dataclass(slots=True)
class EngineUndoToken:
    move: Move
    player: int
    captured: tuple[tuple[int, int, int], ...]
    captures_before: tuple[int, int]
    current_player_before: int
    game_over_before: bool
    winner_before: int | None
    win_reason_before: str | None
    is_draw_before: bool
    winning_line_before: list[Move] | None
    pending_win_before: dict | None
    move_history_size: int
    action_history_size: int
    state_version_before: int
    result: MoveResult


class GomokuRulesAdapter:
    """Implement the AI protocol while leaving ``GomokuGame`` unchanged."""

    def __init__(self, tactical_cache_size: int = 20_000) -> None:
        self._tactical_cache: dict[Hashable, TacticalMoves] = {}
        self._tactical_cache_size = tactical_cache_size
        self._analysis_cache: dict[tuple[int, int, int, Move], tuple[bool, bool, bool, tuple[Move, ...]]] = {}
        self._version_counter = 0

    def _bump_version(self, game: GomokuGame) -> None:
        self._version_counter += 1
        setattr(game, "_ai_state_version", self._version_counter)

    def clone_state(self, state: object) -> object:
        return copy.deepcopy(self._game(state))

    @staticmethod
    def _game(state: object) -> GomokuGame:
        if not isinstance(state, GomokuGame):
            raise TypeError("state must be a GomokuGame")
        return state

    @staticmethod
    def _actions(game: GomokuGame) -> list[PlayedMove]:
        actions = getattr(game, "_ai_action_history", None)
        if actions is None:
            actions = [PlayedMove((r, c), player) for r, c, player in game.move_history]
            setattr(game, "_ai_action_history", actions)
        return actions

    def is_legal_move(self, state: object, move: Move, player: int) -> bool:
        game = self._game(state)
        row, col = move
        if player != game.current_player or not game.is_valid_move(row, col):
            return False
        return self._move_analysis(game, move, player)[0]

    def apply_move(self, state: object, move: Move, player: int) -> object:
        game = self._game(state)
        if not self.is_legal_move(game, move, player):
            raise ValueError(f"illegal move {move} for player {player}")

        row, col = move
        captured = tuple(
            (r, c, game.board[r][c])
            for pair in game._find_captures(row, col, player)
            for r, c in pair
        )
        actions = self._actions(game)
        snapshot = {
            "captures_before": (game.captures[BLACK], game.captures[WHITE]),
            "current_player_before": game.current_player,
            "game_over_before": game.game_over,
            "winner_before": game.winner,
            "win_reason_before": game.win_reason,
            "is_draw_before": game.is_draw,
            "winning_line_before": copy.deepcopy(game.winning_line),
            "pending_win_before": copy.deepcopy(game.pending_win),
            "move_history_size": len(game.move_history),
            "action_history_size": len(actions),
            "state_version_before": getattr(game, "_ai_state_version", 0),
        }
        result = game.make_move(row, col)
        if not result.success:
            raise RuntimeError(f"engine rejected previously legal move {move}: {result.message}")
        actions.append(
            PlayedMove(
                move,
                player,
                captured_stones=len(result.captured_cells),
                created_threat=result.pending_win,
            )
        )
        self._bump_version(game)
        return EngineUndoToken(move, player, captured, result=result, **snapshot)

    def undo_move(self, state: object, undo_token: object) -> None:
        game = self._game(state)
        if not isinstance(undo_token, EngineUndoToken):
            raise TypeError("undo token was not created by this adapter")
        token = undo_token
        row, col = token.move
        game.board[row][col] = EMPTY
        for r, c, stone in token.captured:
            game.board[r][c] = stone
        game.captures[BLACK], game.captures[WHITE] = token.captures_before
        game.current_player = token.current_player_before
        game.game_over = token.game_over_before
        game.winner = token.winner_before
        game.win_reason = token.win_reason_before
        game.is_draw = token.is_draw_before
        game.winning_line = copy.deepcopy(token.winning_line_before)
        game.pending_win = copy.deepcopy(token.pending_win_before)
        del game.move_history[token.move_history_size:]
        del self._actions(game)[token.action_history_size:]
        self._bump_version(game)

    def get_result(self, state: object) -> GameResult:
        game = self._game(state)
        return GameResult(game.game_over, game.winner, game.win_reason or ("draw" if game.is_draw else ""))

    def get_current_player(self, state: object) -> int:
        return self._game(state).current_player

    def get_capture_count(self, state: object, player: int) -> int:
        return self._game(state).captures[player]

    def get_board_cell(self, state: object, row: int, col: int) -> int:
        return self._game(state).board[row][col]

    def get_state_hash_data(self, state: object) -> Hashable:
        game = self._game(state)
        pending = None
        if game.pending_win:
            pending = (
                game.pending_win["player"],
                tuple(tuple(cell) for cell in game.pending_win["line"]),
            )
        recent = tuple(self._actions(game)[-4:])
        return (
            tuple(cell for row in game.board for cell in row),
            game.current_player,
            game.captures[BLACK],
            game.captures[WHITE],
            game.game_over,
            game.winner,
            game.win_reason,
            game.is_draw,
            pending,
            recent,
        )

    def _analyze_move(
        self, game: GomokuGame, move: Move, player: int
    ) -> tuple[bool, bool, bool, tuple[Move, ...]]:
        """Return legality, secure alignment, capture win, and captures."""
        row, col = move
        if game.board[row][col] != EMPTY:
            return False, False, False, ()
        pairs = game._find_captures(row, col, player)
        if not pairs and game._creates_double_three(row, col, player):
            return False, False, False, ()
        captured = tuple(cell for pair in pairs for cell in pair)
        game.board[row][col] = player
        for r, c in captured:
            game.board[r][c] = EMPTY
        try:
            line = game._check_alignment(row, col, player)
            secure = bool(line and not game._line_is_capturable(line, player))
            capture_win = game.captures[player] + len(captured) >= game.stones_to_win_by_capture
            return True, secure, capture_win, captured
        finally:
            game.board[row][col] = EMPTY
            opponent = game.opponent(player)
            for r, c in captured:
                game.board[r][c] = opponent

    def _move_analysis(
        self, game: GomokuGame, move: Move, player: int
    ) -> tuple[bool, bool, bool, tuple[Move, ...]]:
        version = getattr(game, "_ai_state_version", 0)
        key = (id(game), version, player, move)
        cached = self._analysis_cache.get(key)
        if cached is not None:
            return cached
        result = self._analyze_move(game, move, player)
        if len(self._analysis_cache) >= self._tactical_cache_size * 4:
            self._analysis_cache.clear()
        self._analysis_cache[key] = result
        return result

    def _immediate_threats(self, game: GomokuGame, player: int) -> tuple[set[Move], set[Move]]:
        alignments: set[Move] = set()
        capture_wins: set[Move] = set()
        for move in self._local_empty_moves(game):
            legal, secure, capture_win, _ = self._move_analysis(game, move, player)
            if not legal:
                continue
            if secure:
                alignments.add(move)
            if capture_win:
                capture_wins.add(move)
        return alignments, capture_wins

    @staticmethod
    def _local_empty_moves(game: GomokuGame) -> tuple[Move, ...]:
        """Union of radius-two windows; every one-move tactic is local."""
        size = game.board_size
        candidates: set[Move] = set()
        occupied = False
        for row in range(size):
            for col in range(size):
                if game.board[row][col] == EMPTY:
                    continue
                occupied = True
                for near_row in range(max(0, row - 2), min(size, row + 3)):
                    for near_col in range(max(0, col - 2), min(size, col + 3)):
                        if game.board[near_row][near_col] == EMPTY:
                            candidates.add((near_row, near_col))
        if not occupied:
            center = size // 2
            return ((center, center),)
        return tuple(sorted(candidates))

    def get_tactical_moves(self, state: object, player: int) -> TacticalMoves:
        game = self._game(state)
        if player != game.current_player or game.game_over:
            return TacticalMoves()
        cache_key = (self.get_state_hash_data(game), player)
        cached = self._tactical_cache.get(cache_key)
        if cached is not None:
            return cached

        wins: list[Move] = []
        capture_wins: list[Move] = []
        pending_breaks: list[Move] = []
        captures: list[Move] = []
        opponent = game.opponent(player)
        pending_line = (
            set(map(tuple, game.pending_win["line"]))
            if game.pending_win and game.pending_win["player"] == opponent
            else set()
        )
        opponent_alignments, opponent_capture_wins = self._immediate_threats(game, opponent)

        for move in self._local_empty_moves(game):
            legal, secure, capture_win, captured = self._move_analysis(game, move, player)
            if not legal:
                continue
            if secure:
                wins.append(move)
            if capture_win:
                capture_wins.append(move)
            if captured:
                captures.append(move)
            if pending_line.intersection(captured):
                pending_breaks.append(move)

        # Occupying the opponent's terminal square is the common immediate
        # defense. Capturing defenses are also retained via ``captures``.
        legal = set(wins + capture_wins + pending_breaks + captures)
        legal.update(
            move for move in opponent_alignments | opponent_capture_wins
            if self.is_legal_move(game, move, player)
        )
        result = TacticalMoves(
            secure_wins=tuple(sorted(wins)),
            capture_wins=tuple(sorted(capture_wins)),
            pending_win_breaks=tuple(sorted(pending_breaks)),
            immediate_loss_blocks=tuple(sorted(opponent_alignments & legal)),
            capture_win_defenses=tuple(sorted(opponent_capture_wins & legal)),
            captures=tuple(sorted(captures)),
        )
        if len(self._tactical_cache) >= self._tactical_cache_size:
            self._tactical_cache.clear()
        self._tactical_cache[cache_key] = result
        return result

    def get_recent_moves(self, state: object, limit: int) -> tuple[PlayedMove, ...]:
        return tuple(self._actions(self._game(state))[-limit:])
