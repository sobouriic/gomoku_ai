
import time
import tkinter as tk
from tkinter import messagebox

from .gomuku_backend import GomokuGame, BLACK, WHITE, PLAYER_NAMES

BOARD_SIZE = 19          
CELL_SIZE = 30
MARGIN = 26
STONE_RADIUS = 12

BG_COLOR = "#DCB35C"
LINE_COLOR = "#4A3521"
STAR_POINT_COLOR = "#4A3521"
BLACK_STONE_COLOR = "#1a1a1a"
WHITE_STONE_COLOR = "#f5f5f5"
STONE_OUTLINE = "#333333"
HIGHLIGHT_COLOR = "#ff3b30"
PENDING_COLOR = "#ff9500"
LAST_MOVE_COLOR = "#ff3b30"
CAPTURED_FLASH_COLOR = "#4da6ff"


class GomokuGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Gomoku - Human vs Human")
        self.root.resizable(False, False)

        self.game = GomokuGame(board_size=BOARD_SIZE)

       
        self.suggestion_fn = None

       
        self._move_start_time = None

        canvas_size = MARGIN * 2 + CELL_SIZE * (BOARD_SIZE - 1)

      
        self.status_var = tk.StringVar()
        tk.Label(root, textvariable=self.status_var, font=("Helvetica", 14, "bold"),
                 pady=8).pack()

        
        self.info_var = tk.StringVar()
        tk.Label(root, textvariable=self.info_var, font=("Helvetica", 10),
                 fg="#555555").pack()

        
        self.canvas = tk.Canvas(
            root, width=canvas_size, height=canvas_size, bg=BG_COLOR, highlightthickness=0
        )
        self.canvas.pack(padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        
        controls = tk.Frame(root)
        controls.pack(pady=(0, 10))
        tk.Button(controls, text="New Game", command=self.new_game, width=12).grid(
            row=0, column=0, padx=5)
        tk.Button(controls, text="Undo", command=self.undo_move, width=12).grid(
            row=0, column=1, padx=5)
        self.suggest_btn = tk.Button(controls, text="Suggest Move",
                                      command=self.suggest_move, width=12)
        self.suggest_btn.grid(row=0, column=2, padx=5)

        self._draw_board_grid()
        self._update_status()
        self._update_info()

   
    def _board_to_pixel(self, row: int, col: int):
        return MARGIN + col * CELL_SIZE, MARGIN + row * CELL_SIZE

    def _pixel_to_board(self, x: int, y: int):
        col = round((x - MARGIN) / CELL_SIZE)
        row = round((y - MARGIN) / CELL_SIZE)
        return row, col

  
    def _draw_board_grid(self):
        self.canvas.delete("grid")
        size_px = MARGIN * 2 + CELL_SIZE * (BOARD_SIZE - 1)
        for i in range(BOARD_SIZE):
            self.canvas.create_line(MARGIN, MARGIN + i * CELL_SIZE,
                                     size_px - MARGIN, MARGIN + i * CELL_SIZE,
                                     fill=LINE_COLOR, tags="grid")
            self.canvas.create_line(MARGIN + i * CELL_SIZE, MARGIN,
                                     MARGIN + i * CELL_SIZE, size_px - MARGIN,
                                     fill=LINE_COLOR, tags="grid")
        
        for r, c in [(3, 3), (3, 9), (3, 15), (9, 3), (9, 9), (9, 15),
                     (15, 3), (15, 9), (15, 15)]:
            x, y = self._board_to_pixel(r, c)
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3,
                                     fill=STAR_POINT_COLOR, outline="", tags="grid")

    def _draw_stone(self, row, col, player, mark_last=False, mark_pending=False):
        x, y = self._board_to_pixel(row, col)
        color = BLACK_STONE_COLOR if player == BLACK else WHITE_STONE_COLOR
        self.canvas.create_oval(x - STONE_RADIUS, y - STONE_RADIUS,
                                 x + STONE_RADIUS, y + STONE_RADIUS,
                                 fill=color, outline=STONE_OUTLINE, width=1, tags="stones")
        if mark_pending:
            self.canvas.create_oval(x - STONE_RADIUS - 3, y - STONE_RADIUS - 3,
                                     x + STONE_RADIUS + 3, y + STONE_RADIUS + 3,
                                     outline=PENDING_COLOR, width=2, tags="stones")
        elif mark_last:
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3,
                                     fill=LAST_MOVE_COLOR, outline="", tags="stones")

    def _redraw_all_stones(self):
        self.canvas.delete("stones")
        last_move = self.game.move_history[-1] if self.game.move_history else None
        pending_cells = set(self.game.pending_win["line"]) if self.game.pending_win else set()
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                player = self.game.board[r][c]
                if player != 0:
                    is_last = last_move is not None and last_move[0] == r and last_move[1] == c
                    is_pending = (r, c) in pending_cells
                    self._draw_stone(r, c, player, mark_last=is_last, mark_pending=is_pending)
        if self.game.winning_line and self.game.game_over:
            for (r, c) in self.game.winning_line:
                x, y = self._board_to_pixel(r, c)
                self.canvas.create_oval(x - STONE_RADIUS - 4, y - STONE_RADIUS - 4,
                                         x + STONE_RADIUS + 4, y + STONE_RADIUS + 4,
                                         outline=HIGHLIGHT_COLOR, width=3, tags="stones")

    def _update_status(self, message: str = None):
        if message:
            self.status_var.set(message)
            return
        if self.game.game_over:
            if self.game.is_draw:
                self.status_var.set("Draw! The board is full.")
            elif self.game.win_reason == "capture":
                self.status_var.set(f"{PLAYER_NAMES[self.game.winner]} wins by capture! 🎉")
            else:
                self.status_var.set(f"{PLAYER_NAMES[self.game.winner]} wins! 🎉")
        elif self.game.pending_win:
            p = self.game.pending_win["player"]
            opp = self.game.opponent(p)
            self.status_var.set(
                f"{PLAYER_NAMES[p]} has 5 in a row! {PLAYER_NAMES[opp]} can still "
                f"break it by capturing -- last chance now."
            )
        else:
            self.status_var.set(f"{PLAYER_NAMES[self.game.current_player]}'s turn")

    def _update_info(self, last_move_seconds: float = None):
        b_cap = self.game.captures[BLACK]
        w_cap = self.game.captures[WHITE]
        parts = [f"Captures -- Black: {b_cap}/10   White: {w_cap}/10"]
        if last_move_seconds is not None:
            parts.append(f"   |   Last move time: {last_move_seconds:.3f}s")
        self.info_var.set("".join(parts))

   
    def on_canvas_click(self, event):
        if self.game.game_over:
            return

        row, col = self._pixel_to_board(event.x, event.y)
        if not self.game.in_bounds(row, col):
            return

        start = time.perf_counter()
        result = self.game.make_move(row, col)
        elapsed = time.perf_counter() - start

        if not result.success:
            self._update_status(result.message)
            self.root.after(1500, lambda: self._update_status())
            return

        self._redraw_all_stones()
        self._update_status()
        self._update_info(last_move_seconds=elapsed)

        if result.game_over:
            messagebox.showinfo("Game Over", result.message)

       
    def suggest_move(self):
        if self.suggestion_fn is None:
            messagebox.showinfo(
                "Move Suggestion",
                "Move suggestions need the AI module, which isn't plugged in yet.",
            )
            return
        if self.game.game_over:
            return
        suggestion = self.suggestion_fn(self.game)
        if suggestion:
            r, c = suggestion
            messagebox.showinfo("Suggested Move", f"Try row {r}, column {c}.")

    def new_game(self):
        self.game.reset()
        self.canvas.delete("stones")
        self._update_status()
        self._update_info()

    def undo_move(self):
        if self.game.undo_last_move():
            self._redraw_all_stones()
            self._update_status()
            self._update_info()


def main():
    root = tk.Tk()
    GomokuGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
