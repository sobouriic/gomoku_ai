from __future__ import annotations
import time
from .config import AIConfig
from .evaluator import Evaluator
from .models import SearchResult
from .move_generator import MoveGenerator
from .rules_protocol import RulesEngine
from .search import SearchEngine, SearchTimeout
from .transposition import TranspositionTable


class GomokuAI:
    def __init__(self, rules: RulesEngine, config: AIConfig | None = None):
        self.rules = rules
        self.config = config or AIConfig()
        self.generator = MoveGenerator(rules, self.config)
        self.evaluator = Evaluator(rules, self.config)
        self.table = TranspositionTable(self.config.transposition_size)
        self.search = SearchEngine(
            rules, self.config, self.generator, self.evaluator, self.table
        )

    def find_best_move(
        self, state: object, ai_player: int, time_limit_s: float = 0.45
    ) -> SearchResult:
        started = time.perf_counter()
        working = self.rules.clone_state(state)
        legal = self.generator.candidates(working, ai_player)
        fallback = legal[0] if legal else None
        if fallback is None:
            return SearchResult(None, 0, 0, 0, (time.perf_counter() - started) * 1000, (), 0, 0)

        deadline = started + max(0.0, time_limit_s)
        self.search.begin(deadline, ai_player)
        best_move, best_score, best_pv, completed = fallback, 0, (fallback,), 0
        # Staged iterative deepening retains early fallback/PV ordering while
        # avoiding nearly identical work at every intermediate quiet depth.
        depths = [1]
        if self.config.max_depth >= 2:
            depths.append(2)
        if self.config.max_depth > 6:
            depths.append(6)
        if depths[-1] != self.config.max_depth:
            depths.append(self.config.max_depth)
        for depth in depths:
            try:
                score, pv = self.search.search_depth(working, depth)
            except SearchTimeout:
                break
            if pv:
                best_move, best_score, best_pv = pv[0], score, pv
            completed = depth
            if abs(score) >= self.config.mate_score - depth:
                break
        # Defensive final validation protects against a broken adapter/cache bug.
        if not self.rules.is_legal_move(state, best_move, ai_player):
            best_move, best_pv = fallback, (fallback,)
        elapsed = (time.perf_counter() - started) * 1000
        stats = self.search.stats
        return SearchResult(
            best_move, best_score, completed, stats.nodes, elapsed,
            best_pv, stats.cache_hits, stats.cutoffs,
        )
