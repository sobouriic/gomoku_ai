from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from .adapter import EngineUndoToken, GomokuRulesAdapter
from .gomuku_backend import BLACK, WHITE, PLAYER_NAMES
from .gomoku_gui import GomokuGUI
from ai import GomokuAI


class IntegratedGomokuGUI(GomokuGUI):
    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self.root.title("Gomoku")
        self.rules = GomokuRulesAdapter()
        self.ai = GomokuAI(self.rules)
        self.ai_player = WHITE
        self.undo_tokens: list[EngineUndoToken] = []
        self.mode = tk.StringVar(value="human_ai")
        self.ai_busy = False
        self.last_ai_ms: float | None = None

        modes = tk.Frame(root)
        modes.pack(pady=(0, 10))
        tk.Radiobutton(
            modes, text="Human vs AI", variable=self.mode, value="human_ai",
            command=self.new_game,
        ).pack(side=tk.LEFT, padx=8)
        tk.Radiobutton(
            modes, text="Human vs Human", variable=self.mode, value="hotseat",
            command=self.new_game,
        ).pack(side=tk.LEFT, padx=8)

    def _update_info(self, last_move_seconds: float | None = None) -> None:
        # ``last_move_seconds`` is accepted for compatibility with the parent,
        # but only actual AI search time is labeled as AI time.
        b_cap = self.game.captures[BLACK]
        w_cap = self.game.captures[WHITE]
        parts = [f"Captures — Black: {b_cap}/10   White: {w_cap}/10"]
        ai_ms = getattr(self, "last_ai_ms", None)
        if ai_ms is not None:
            parts.append(f"   |   AI thinking time: {ai_ms / 1000:.3f}s")
        self.info_var.set("".join(parts))

    def _apply_permanent(self, move: tuple[int, int], player: int):
        token = self.rules.apply_move(self.game, move, player)
        assert isinstance(token, EngineUndoToken)
        self.undo_tokens.append(token)
        self._redraw_all_stones()
        self._update_status()
        self._update_info()
        if token.result.game_over:
            messagebox.showinfo("Game Over", token.result.message)
        return token.result

    def on_canvas_click(self, event) -> None:
        if self.game.game_over or self.ai_busy:
            return
        if self.mode.get() == "human_ai" and self.game.current_player == self.ai_player:
            return
        row, col = self._pixel_to_board(event.x, event.y)
        move = (row, col)
        player = self.game.current_player
        if not self.rules.is_legal_move(self.game, move, player):
            self._update_status("Illegal move.")
            self.root.after(1500, self._update_status)
            return
        result = self._apply_permanent(move, player)
        if (
            result.success and not result.game_over
            and self.mode.get() == "human_ai"
            and self.game.current_player == self.ai_player
        ):
            self.ai_busy = True
            self._update_status("AI is thinking…")
            self.root.after(10, self.play_ai_turn)

    def _fallback(self, player: int) -> tuple[int, int] | None:
        for row in range(self.game.board_size):
            for col in range(self.game.board_size):
                move = (row, col)
                if self.rules.is_legal_move(self.game, move, player):
                    return move
        return None

    def play_ai_turn(self) -> None:
        try:
            if self.game.game_over or self.game.current_player != self.ai_player:
                return
            try:
                result = self.ai.find_best_move(self.game, self.ai_player, 0.45)
                move = result.move
                self.last_ai_ms = result.elapsed_ms
            except Exception as error:  # keep the application alive per subject
                move = self._fallback(self.ai_player)
                self.last_ai_ms = None
                messagebox.showwarning("AI recovery", f"AI used a safe fallback: {error}")
            if move is None:
                self._update_status("No legal move is available.")
                return
            if not self.rules.is_legal_move(self.game, move, self.ai_player):
                move = self._fallback(self.ai_player)
            if move is not None:
                self._apply_permanent(move, self.ai_player)
        finally:
            self.ai_busy = False
            self._update_info()

    def suggest_move(self) -> None:
        if self.game.game_over or self.ai_busy:
            return
        player = self.game.current_player
        try:
            result = self.ai.find_best_move(self.game, player, 0.45)
        except Exception as error:
            messagebox.showerror("Suggestion failed", str(error))
            return
        self.last_ai_ms = result.elapsed_ms
        self._update_info()
        if result.move is not None:
            row, col = result.move
            messagebox.showinfo(
                "Suggested Move",
                f"{PLAYER_NAMES[player]}: row {row}, column {col}\n"
                f"Depth {result.completed_depth}, {result.elapsed_ms:.1f} ms",
            )

    def new_game(self) -> None:
        self.game.reset()
        if hasattr(self.game, "_ai_action_history"):
            delattr(self.game, "_ai_action_history")
        if hasattr(self, "undo_tokens"):
            self.undo_tokens.clear()
        self.last_ai_ms = None
        self.ai_busy = False
        self.canvas.delete("stones")
        self._update_status()
        self._update_info()

    def undo_move(self) -> None:
        if self.ai_busy or not self.undo_tokens:
            return
        # In human-vs-AI mode, undo a complete human+AI round when possible.
        count = 2 if self.mode.get() == "human_ai" and len(self.undo_tokens) >= 2 else 1
        for _ in range(count):
            self.rules.undo_move(self.game, self.undo_tokens.pop())
        self.last_ai_ms = None
        self._redraw_all_stones()
        self._update_status()
        self._update_info()


def main() -> None:
    root = tk.Tk()
    IntegratedGomokuGUI(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        # A terminal Ctrl+C is a normal user-requested shutdown, not a crash.
        try:
            root.destroy()
        except tk.TclError:
            pass


if __name__ == "__main__":
    main()
