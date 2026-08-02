from __future__ import annotations

from .config import AIConfig
from .models import Move
from .rules_protocol import RulesEngine


class MoveGenerator:
    def __init__(self, rules: RulesEngine, config: AIConfig) -> None:
        self.rules, self.config = rules, config
        n, radius = config.board_size, config.neighborhood_radius
        self.neighbors: tuple[tuple[Move, ...], ...] = tuple(
            tuple(
                (rr, cc)
                for rr in range(max(0, r - radius), min(n, r + radius + 1))
                for cc in range(max(0, c - radius), min(n, c + radius + 1))
                if rr != r or cc != c
            )
            for r in range(n) for c in range(n)
        )

    def candidates(self, state: object, player: int) -> list[Move]:
        n, occupied, indices = self.config.board_size, False, set()
        get = self.rules.get_board_cell
        for r in range(n):
            for c in range(n):
                if get(state, r, c):
                    occupied = True
                    for rr, cc in self.neighbors[r * n + c]:
                        if get(state, rr, cc) == 0:
                            indices.add(rr * n + cc)
        if not occupied:
            center = n // 2
            return [(center, center)] if self.rules.is_legal_move(
                state, (center, center), player
            ) else self._all_legal(state, player)
        moves = [divmod(index, n) for index in indices]
        moves = [m for m in moves if self.rules.is_legal_move(state, m, player)]
        moves.sort(key=lambda m: self.static_score(state, m, player), reverse=True)
        return moves or self._all_legal(state, player)

    def _all_legal(self, state: object, player: int) -> list[Move]:
        n = self.config.board_size
        return [
            (r, c) for r in range(n) for c in range(n)
            if self.rules.get_board_cell(state, r, c) == 0
            and self.rules.is_legal_move(state, (r, c), player)
        ]

    def static_score(self, state: object, move: Move, player: int) -> int:
        """Order by nearby friendly/opposing stones; deterministic center tie-break."""
        r, c = move
        n, score = self.config.board_size, 0
        other = 3 - player
        get = self.rules.get_board_cell
        for dr, dc in ((1, 0), (0, 1), (1, 1), (1, -1)):
            for sign in (-1, 1):
                rr, cc = r + dr * sign, c + dc * sign
                if 0 <= rr < n and 0 <= cc < n:
                    cell = get(state, rr, cc)
                    score += 5 if cell == player else 6 if cell == other else 0
        center = n // 2
        return score * 100 - abs(r - center) - abs(c - center)
