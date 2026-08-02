from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class AIConfig:
    board_size: int = 19
    max_depth: int = 10
    neighborhood_radius: int = 2
    root_candidate_limit: int = 6
    middle_candidate_limit: int = 2
    deep_candidate_limit: int = 1
    middle_plies: int = 2
    deadline_check_interval: int = 32
    transposition_size: int = 100_000
    mate_score: int = 1_000_000_000
    capture_win_stones: int = 10

    open_four: int = 180_000
    closed_four: int = 35_000
    broken_four: int = 42_000
    open_three: int = 8_000
    broken_three: int = 4_000
    closed_three: int = 900
    open_two: int = 300
    closed_two: int = 60
    capture_stone: int = 3_500
    immediate_capture: int = 2_500
    vulnerable_pair: int = 2_000
    one_capture_from_win: int = 160_000
    pending_line: int = 220_000
    defense_multiplier_percent: int = 110
    potential_one: int = 5
    potential_two: int = 45
    potential_three: int = 650
    potential_four: int = 18_000
    recent_capture: int = 900
    recent_threat: int = 500

    def candidate_limit(self, ply: int) -> int:
        if ply == 0:
            return self.root_candidate_limit
        return self.middle_candidate_limit if ply < self.middle_plies else self.deep_candidate_limit
