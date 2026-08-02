from __future__ import annotations

import random
from collections.abc import Sequence


class ZobristHasher:
    def __init__(self, board_size: int = 19, seed: int = 0x474F4D4F4B55) -> None:
        rng = random.Random(seed)
        self.table = tuple(
            (0, rng.getrandbits(64), rng.getrandbits(64))
            for _ in range(board_size * board_size)
        )
        self.turn = (0, rng.getrandbits(64), rng.getrandbits(64))

    def hash_board(self, board: Sequence[int], current_player: int) -> int:
        value = self.turn[current_player]
        for index, stone in enumerate(board):
            if stone:
                value ^= self.table[index][stone]
        return value
