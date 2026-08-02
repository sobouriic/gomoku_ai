# Gomoku

A complete playable implementation of the Gomoku version 3.3 subject, written
in Python 3.11 using only the standard library at runtime. The project provides
a 19×19 graphical game, human-versus-AI and human-versus-human modes, captures,
double-three restrictions, endgame-capture resolution, a Minimax AI, move
suggestions, and a visible AI timer.

## Requirements

- Python 3.11 or newer
- Tkinter for the graphical interface
- GNU Make

On Debian-based systems, Tkinter can be installed with the system package
`python3-tk` if it is not already available.

## Build and run

Build the required executable:

```bash
make
```

Launch the game:

```bash
./Gomoku
```

The application can also be started directly:

```bash
python3 -m game
```

Close the application using the window close button or Ctrl+C. Both methods
exit cleanly.

### Makefile targets

```bash
make          # Build the Gomoku executable
make clean    # Remove Python and tool caches
make fclean   # Remove caches and the Gomoku executable
make re       # Rebuild everything
```

Running `make` twice does not rebuild the executable when no source changed.

## How to play

The board contains 19 rows and 19 columns. Stones are placed on intersections.
Black moves first, followed by White, and the players alternate after each
legal move.

The interface offers two modes:

### Human versus AI

- The human plays Black.
- The AI plays White.
- Click an empty legal intersection to play.
- After a human move, the AI automatically searches and responds.
- The interface displays the AI's measured thinking time.

### Human versus Human

- Two people alternate on the same computer.
- The **Suggest Move** button asks the AI for a recommendation for the current
  player.
- The suggestion dialog displays the proposed coordinates, completed search
  depth, and thinking time.

### Controls

- **New Game** resets the complete position and capture counters.
- **Undo** restores the previous position. In Human-versus-AI mode it normally
  undoes a complete human-and-AI round.
- **Suggest Move** asks the AI for a legal move without changing the board.
- **Human vs AI / Human vs Human** changes mode and starts a new game.

## Game rules

### Board and turns

The board is a 19×19 Goban with no limit on the number of stones. A move places
one stone on an empty legal intersection. A move outside the board or on an
occupied position is illegal.

The internal values are:

```text
0 = empty
1 = Black
2 = White
```

### Alignment victory

A player may win by connecting five or more stones in one of four directions:

```text
Horizontal       ─
Vertical         │
Main diagonal    ↘
Anti-diagonal    ↙
```

Six or more consecutive stones also count. Because of the endgame-capture
rule, a visible line of five is not automatically a final victory.

### Pair captures

A player captures exactly two opposing stones by actively completing a flank:

```text
X O O _   →   X O O X   →   X _ _ X
```

The captured stones are removed and their intersections become playable
again. Captures work horizontally, vertically, and diagonally. The rule only
captures a pair—not one stone and not a sequence longer than two.

Moving one's own stone into an already flanked pair does not cause that pair to
be captured automatically. The capturing player must actively place the stone
that completes the capture.

### Capture victory

A player wins after capturing ten opponent stones:

```text
5 captured pairs = 10 captured stones = victory
```

This is independent of alignment victory. A player can therefore win without
having five visible stones in a row. The GUI displays both capture counters as
values from 0 to 10.

### Endgame capture

When a player creates a line of five or more, the engine checks whether the
opponent can immediately capture a pair belonging to that line.

- If the line cannot be broken, the alignment wins immediately.
- If it can be broken, the alignment becomes pending and the opponent receives
  one response.
- If that response captures stones from the line, the line is broken and play
  continues.
- If the response does not break it, the player who created the alignment wins.
- If the response produces the opponent's tenth captured stone, the opponent
  wins by capture.

Final terminal truth always comes from the game engine. The AI never assumes
that merely seeing five stones means the game has ended.

### Double-three restriction

A free-three is a group of three stones that can develop into an open four—a
four-stone alignment with both ends unobstructed. A move that simultaneously
creates two free-threes is normally forbidden.

The subject defines one exception: a move that creates a double-three is legal
if that same move also captures a pair. Legal move validation, including this
exception, is owned by the game engine and used by both the GUI and AI.

### Draw

If the board becomes full and neither player has won, the game ends in a draw.

## Project structure

```text
.
├── ai/
│   ├── __init__.py
│   ├── ai.py
│   ├── config.py
│   ├── debug.py
│   ├── evaluator.py
│   ├── models.py
│   ├── move_generator.py
│   ├── rules_protocol.py
│   ├── search.py
│   ├── transposition.py
│   └── zobrist.py
├── game/
│   ├── __init__.py
│   ├── __main__.py
│   ├── adapter.py
│   ├── gomoku_gui.py
│   ├── gomuku_backend.py
│   └── gui.py
├── Makefile
├── gomoku_launcher.sh
├── pyproject.toml
└── README.md
```

### Game package

- `gomuku_backend.py` stores the board and implements placement, captures,
  alignment detection, capture victory, pending alignment resolution,
  double-three validation, draw detection, and game state.
- `gomoku_gui.py` contains the reusable Tkinter board, drawing code, status
  display, coordinate conversion, and basic controls.
- `gui.py` extends the base GUI with Human-versus-AI mode, AI suggestions,
  actual AI timing, safe fallback behavior, and complete integrated undo.
- `adapter.py` is the boundary between the game engine and search. It exposes
  official rule truth to the AI and supplies private reversible operations.
- `__main__.py` starts the integrated graphical application.

The two GUI files have separate responsibilities: `gomoku_gui.py` owns basic
presentation, while `gui.py` owns final AI-integrated behavior.

### AI package

- `ai.py` provides the public `GomokuAI.find_best_move` entry point.
- `search.py` implements explicit Minimax, alpha-beta pruning, staged iterative
  deepening, deadline handling, and principal-variation construction.
- `move_generator.py` generates local legal candidates and orders promising
  moves first.
- `evaluator.py` scores non-terminal positions.
- `config.py` contains candidate limits, search settings, and heuristic weights.
- `transposition.py` stores reusable search results in a bounded cache.
- `zobrist.py` provides deterministic board-hashing support.
- `rules_protocol.py` defines the typed engine/search contract.
- `models.py` contains moves, game results, tactical data, and search results.
- `debug.py` formats AI reasoning statistics.

## AI public interface

```python
from ai import GomokuAI
from game import GomokuRulesAdapter

rules = GomokuRulesAdapter()
ai = GomokuAI(rules)

result = ai.find_best_move(
    state=game_state,
    ai_player=game_state.current_player,
    time_limit_s=0.45,
)
```

The returned `SearchResult` contains:

- `move`: selected `(row, column)`, or `None` when no legal move exists.
- `score`: integer evaluation from the AI's perspective.
- `completed_depth`: last completely finished iteration.
- `nodes`: number of searched positions.
- `elapsed_ms`: measured AI thinking time.
- `principal_variation`: expected best sequence for both players.
- `cache_hits`: reused transposition entries.
- `cutoffs`: alpha-beta prunings.

## Minimax

The game tree alternates between two kinds of levels:

- MAX: the AI chooses the child with the highest score.
- MIN: the opponent chooses the child with the lowest score.

For example, suppose Move A allows final scores `10`, `4`, and `8`, while Move
B allows `7`, `6`, and `5`. A strong opponent chooses the worst result for the
AI, so A is valued at `4` and B at `5`. MAX chooses B.

This models an opponent who also plays correctly instead of expecting the
opponent to make mistakes.

## Alpha-beta pruning

Searching every branch of a 19×19 board is impossible. Alpha-beta keeps two
bounds:

- Alpha: the best guaranteed score already found for MAX.
- Beta: the best guaranteed score already found for MIN.

When `alpha >= beta`, remaining siblings cannot affect the final choice and are
skipped. Move ordering makes pruning more effective by examining wins,
defenses, captures, and strong patterns before quiet moves.

## Candidate generation

The AI does not search every empty board position. It builds the union of
radius-two neighborhoods around occupied cells. Separate groups of stones
produce separate local search windows instead of one large rectangle. On an
empty board, the center `(9, 9)` is preferred.

Quiet candidate counts become narrower at deeper plies to make ten-ply search
possible within the deadline. Rule-aware tactical moves bypass those limits:

- Secure alignment wins
- Capture wins
- Pending-line breaks
- Immediate-loss blocks
- Capture-win defenses
- Captures

This distinction is important: selective search limits quiet choices without
discarding engine-reported forced moves.

## Iterative deepening and time management

Search uses staged iterative depths 1, 2, 6, and 10. Shallow iterations provide
a safe answer quickly and improve move ordering for deeper search. The final
target is ten plies.

The deadline uses `time.perf_counter()`. If time expires during a deeper
iteration, search returns the result from the last fully completed iteration.
It never falsely reports an unfinished depth. A proven terminal victory or loss
may stop early because deeper search cannot change that result.

The default move budget is 0.45 seconds. The GUI displays `elapsed_ms` from the
actual AI search rather than measuring ordinary board-processing time.

## Heuristic evaluation

When the search reaches its depth limit without a terminal result, it evaluates
the position with integers. Positive values favor the AI; negative values favor
the opponent.

The evaluator scans all horizontal, vertical, and diagonal lines and recognizes:

- Open, closed, and broken fours
- Open, closed, and broken threes
- Open and closed twos
- Opponent-free five-cell development windows
- Immediate capture opportunities
- Capture progress
- Vulnerable pairs
- One-capture-away danger
- Recent captures and created threats

Both players are evaluated. Opponent threats receive slightly greater urgency
than equal non-forcing attacks, encouraging necessary defense.

Terminal results do not come from pattern matching. They come exclusively from
the engine because a visible alignment may still be capture-breakable.
`MATE_SCORE` is much larger than normal heuristic values, and terminal scores
include ply so faster wins and slower losses are preferred.

## Apply/undo safety

The AI clones the live state once and searches only that private copy. Each
imagined move produces an undo token. Undo restores:

- The placed stone
- Every captured stone
- Capture counters
- Current player
- Pending alignment state
- Winner, reason, and draw state
- Winning line
- Move and action histories

Recursive search uses `try/finally`, so undo still executes when a timeout is
raised. The live GUI state is therefore unchanged by suggestions or search.

## Transposition table

Different move orders may reach equivalent positions. The bounded
transposition table stores the position's depth, score, bound type, best move,
and principal variation.

Cache keys include the complete board, player to move, capture counters,
terminal state, pending alignment, recent dynamic context, and AI player. Ply
is also included because terminal scores encode mate distance.

## Debugging and defense

The AI exposes its move, score, completed depth, visited nodes, elapsed time,
principal variation, cache hits, and cutoffs. These values help explain why a
move was selected and identify performance problems.

During defense, be prepared to explain:

1. MAX and MIN levels in Minimax.
2. How alpha and beta safely remove irrelevant branches.
3. Why local candidate windows are required on a 19×19 board.
4. Why tactical moves bypass quiet candidate limits.
5. Every major heuristic feature and its relative weight.
6. Why final victory truth belongs to the engine.
7. How private cloning and `try/finally` guarantee state restoration.
8. Why completed depth remains truthful after timeout.
9. How the GUI displays actual AI thinking time.

## Performance

The subject requires average AI thinking time below approximately 0.5 seconds.
Timing varies by machine and position. Quiet positions can complete ten plies;
complex tactical positions may return the last completed shallower iteration
when the deadline expires. The visible GUI timer should be checked across many
complete games, not only one opening move.

## Private development tests

Automated tests are kept outside the submission repository. They cover
Minimax, alpha-beta, candidates, patterns, captures, double-three capture
exceptions, pending alignments, apply/undo restoration, timeout safety,
determinism, cache behavior, and real engine integration. They are development
tools and are not imported by the running game.
