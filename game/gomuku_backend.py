import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

EMPTY = 0
BLACK = 1  
WHITE = 2

PLAYER_NAMES = {BLACK: "Black", WHITE: "White"}

BOARD_SIZE = 19
WIN_LENGTH = 5
STONES_TO_WIN_BY_CAPTURE = 10  


ALL_DIRECTIONS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]


AXIS_DIRECTIONS = [(0, 1), (1, 0), (1, 1), (1, -1)]

Cell = Tuple[int, int]


@dataclass
class MoveResult:
    
    success: bool
    message: str = ""
    row: Optional[int] = None
    col: Optional[int] = None
    player: Optional[int] = None
    game_over: bool = False
    winner: Optional[int] = None
    win_reason: Optional[str] = None       
    is_draw: bool = False
    winning_line: Optional[List[Cell]] = None
    captured_cells: List[Cell] = field(default_factory=list)
    pending_win: bool = False           


class GomokuGame:
    def __init__(self, board_size: int = BOARD_SIZE, win_length: int = WIN_LENGTH,
                 stones_to_win_by_capture: int = STONES_TO_WIN_BY_CAPTURE):
        self.board_size = board_size
        self.win_length = win_length
        self.stones_to_win_by_capture = stones_to_win_by_capture
        self.reset()

 
    def reset(self) -> None:
        self.board: List[List[int]] = [[EMPTY] * self.board_size for _ in range(self.board_size)]
        self.current_player: int = BLACK
        self.move_history: List[Tuple[int, int, int]] = []
        self.game_over: bool = False
        self.winner: Optional[int] = None
        self.win_reason: Optional[str] = None
        self.is_draw: bool = False
        self.winning_line: Optional[List[Cell]] = None
      
        self.captures = {BLACK: 0, WHITE: 0}

        self.pending_win: Optional[dict] = None


    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.board_size and 0 <= col < self.board_size

    def is_valid_move(self, row: int, col: int) -> bool:

        if self.game_over:
            return False
        if not self.in_bounds(row, col):
            return False
        return self.board[row][col] == EMPTY

    def get_board_state(self) -> List[List[int]]:
        return [row[:] for row in self.board]

    def opponent(self, player: int) -> int:
        return WHITE if player == BLACK else BLACK


    def make_move(self, row: int, col: int) -> MoveResult:
 
        try:
            row, col = int(row), int(col)
        except (TypeError, ValueError):
            return MoveResult(success=False, message="Move coordinates must be integers.")

        if self.game_over:
            return MoveResult(success=False, message="Game is already over.")
        if not self.in_bounds(row, col):
            return MoveResult(success=False, message="Move is outside the board.")
        if self.board[row][col] != EMPTY:
            return MoveResult(success=False, message="That cell is already occupied.")

        player = self.current_player
        opponent = self.opponent(player)

        capture_groups = self._find_captures(row, col, player)


        if not capture_groups and self._creates_double_three(row, col, player):
            return MoveResult(
                success=False,
                message="Illegal move: this would create a double-three (forbidden).",
            )


        self.board[row][col] = player
        self.move_history.append((row, col, player))

        captured_cells: List[Cell] = []
        for pair in capture_groups:
            for (r, c) in pair:
                self.board[r][c] = EMPTY
                captured_cells.append((r, c))
        if captured_cells:
            self.captures[player] += len(captured_cells)

        if self.captures[player] >= self.stones_to_win_by_capture:
            self.game_over = True
            self.winner = player
            self.win_reason = "capture"
            return MoveResult(
                success=True, row=row, col=col, player=player, game_over=True,
                winner=player, win_reason="capture", captured_cells=captured_cells,
                message=f"{PLAYER_NAMES[player]} wins by capturing "
                        f"{self.captures[player]} stones!",
            )


        if self.pending_win and self.pending_win["player"] == opponent:
            line = self.pending_win["line"]
            broke_the_line = any(cell in line for cell in captured_cells)
            if broke_the_line:
                self.pending_win = None
          
            else:
                self.game_over = True
                self.winner = opponent
                self.win_reason = "alignment"
                self.winning_line = line
                return MoveResult(
                    success=True, row=row, col=col, player=player, game_over=True,
                    winner=opponent, win_reason="alignment", winning_line=line,
                    captured_cells=captured_cells,
                    message=f"{PLAYER_NAMES[opponent]} wins by alignment "
                            f"(the line was not broken in time)!",
                )

     
        line = self._check_alignment(row, col, player)
        if line:
            if self._line_is_capturable(line, player):
                self.pending_win = {"player": player, "line": line}
                self.current_player = opponent
                return MoveResult(
                    success=True, row=row, col=col, player=player, game_over=False,
                    winning_line=line, captured_cells=captured_cells, pending_win=True,
                    message=f"{PLAYER_NAMES[player]} aligned {len(line)} in a row, "
                            f"but {PLAYER_NAMES[opponent]} can still break it by "
                            f"capturing -- one move to do so!",
                )
            else:
                self.game_over = True
                self.winner = player
                self.win_reason = "alignment"
                self.winning_line = line
                return MoveResult(
                    success=True, row=row, col=col, player=player, game_over=True,
                    winner=player, win_reason="alignment", winning_line=line,
                    captured_cells=captured_cells,
                    message=f"{PLAYER_NAMES[player]} wins by alignment!",
                )

 
        if self._is_board_full():
            self.game_over = True
            self.is_draw = True
            return MoveResult(
                success=True, row=row, col=col, player=player, game_over=True,
                is_draw=True, captured_cells=captured_cells,
                message="It's a draw! The board is full.",
            )

       
        self.current_player = opponent
        msg = f"{PLAYER_NAMES[opponent]}'s turn."
        if captured_cells:
            msg = (f"{PLAYER_NAMES[player]} captured {len(captured_cells)} stone(s). "
                   + msg)
        return MoveResult(
            success=True, row=row, col=col, player=player, game_over=False,
            captured_cells=captured_cells, message=msg,
        )

    def undo_last_move(self) -> bool:

        if not self.move_history:
            return False
        row, col, player = self.move_history.pop()
        self.board[row][col] = EMPTY
        self.current_player = player
        self.game_over = False
        self.winner = None
        self.win_reason = None
        self.is_draw = False
        self.winning_line = None
        self.pending_win = None
        return True


    def _find_captures(self, row: int, col: int, player: int) -> List[List[Cell]]:

        opponent = self.opponent(player)
        groups: List[List[Cell]] = []
        for dr, dc in ALL_DIRECTIONS:
            r1, c1 = row + dr, col + dc
            r2, c2 = row + 2 * dr, col + 2 * dc
            r3, c3 = row + 3 * dr, col + 3 * dc
            if not self.in_bounds(r3, c3):
                continue
            if (self.board[r1][c1] == opponent and
                    self.board[r2][c2] == opponent and
                    self.board[r3][c3] == player):
                groups.append([(r1, c1), (r2, c2)])
        return groups

    def _check_alignment(self, row: int, col: int, player: int) -> Optional[List[Cell]]:
        for dr, dc in AXIS_DIRECTIONS:
            line = [(row, col)]
            r, c = row + dr, col + dc
            while self.in_bounds(r, c) and self.board[r][c] == player:
                line.append((r, c))
                r += dr
                c += dc
            r, c = row - dr, col - dc
            while self.in_bounds(r, c) and self.board[r][c] == player:
                line.insert(0, (r, c))
                r -= dr
                c -= dc
            if len(line) >= self.win_length:
                return line
        return None

    def _line_is_capturable(self, line: List[Cell], player: int) -> bool:

        opponent = self.opponent(player)
        checked_pairs = set()
        for (r, c) in line:
            for dr, dc in AXIS_DIRECTIONS:
                for sign in (1, -1):
                    ddr, ddc = dr * sign, dc * sign
                    nr, nc = r + ddr, c + ddc
                    if not self.in_bounds(nr, nc) or self.board[nr][nc] != player:
                        continue
                    pair_key = frozenset({(r, c), (nr, nc)})
                    if pair_key in checked_pairs:
                        continue
                    checked_pairs.add(pair_key)
                    before = (r - ddr, c - ddc)
                    after = (nr + ddr, nc + ddc)
                    if (self.in_bounds(*before) and self.board[before[0]][before[1]] == opponent and
                            self.in_bounds(*after) and self.board[after[0]][after[1]] == EMPTY):
                        return True
                    if (self.in_bounds(*after) and self.board[after[0]][after[1]] == opponent and
                            self.in_bounds(*before) and self.board[before[0]][before[1]] == EMPTY):
                        return True
        return False

    def _is_board_full(self) -> bool:
        return all(cell != EMPTY for row in self.board for cell in row)


    _FREE_THREE_PATTERNS = [
        r"\.XXX\.",    
        r"\.XX\.X\.",   
        r"\.X\.XX\.",   
    ]

    def _line_string(self, row: int, col: int, dr: int, dc: int, player: int,
                      radius: int = 4) -> str:
        chars = []
        for i in range(-radius, radius + 1):
            r, c = row + i * dr, col + i * dc
            if not self.in_bounds(r, c):
                chars.append("O")  
            elif self.board[r][c] == player:
                chars.append("X")
            elif self.board[r][c] == EMPTY:
                chars.append(".")
            else:
                chars.append("O")
        return "".join(chars)

    def _has_free_three_through_center(self, s: str, center_idx: int) -> bool:
        for pattern in self._FREE_THREE_PATTERNS:
            for m in re.finditer(f"(?={pattern})", s): 
                start = m.start()
                match_len = len(re.match(pattern, s[start:]).group(0))
                end = start + match_len - 1
                if start <= center_idx <= end:
                    return True
        return False

    def _creates_double_three(self, row: int, col: int, player: int) -> bool:

        self.board[row][col] = player  
        free_three_count = 0
        for dr, dc in AXIS_DIRECTIONS:
            s = self._line_string(row, col, dr, dc, player)
            if self._has_free_three_through_center(s, radius_center := 4):
                free_three_count += 1
        self.board[row][col] = EMPTY  
        return free_three_count >= 2



if __name__ == "__main__":
    print("== Alignment win test ==")
    game = GomokuGame()
    for r, c in [(5, 5), (0, 0), (5, 6), (0, 1), (5, 7), (0, 2), (5, 8), (0, 3), (5, 9)]:
        res = game.make_move(r, c)
        print(f"  ({r},{c}) P{res.player}: {res.message}")
    assert game.game_over and game.winner == BLACK

    print("\n== Capture test ==")
    game = GomokuGame()
   
    game.board[5][5] = BLACK
    game.board[5][6] = WHITE
    game.board[5][7] = WHITE
    game.current_player = BLACK
    res = game.make_move(5, 8)
    print(f"  Capture move: {res.message}, captured={res.captured_cells}")
    assert game.board[5][6] == EMPTY and game.board[5][7] == EMPTY
    assert game.captures[BLACK] == 2

    print("\n== Double-three rejection test ==")
    game = GomokuGame()
    game.board[5][5] = BLACK
    game.board[5][7] = BLACK
    game.board[7][5] = BLACK
    game.board[7][7] = BLACK
    game.current_player = BLACK

    game2 = GomokuGame()
    game2.board[5][4] = BLACK
    game2.board[5][5] = BLACK
    game2.board[4][6] = BLACK
    game2.board[3][6] = BLACK
    game2.current_player = BLACK
    res = game2.make_move(5, 6)  
    print(f"  Move result: success={res.success}, message={res.message}")

    print("\nAll manual checks ran.")
