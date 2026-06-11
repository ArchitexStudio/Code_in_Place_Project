"""Simulate a game between the drafted offense and defense."""

from __future__ import annotations

import random
from dataclasses import dataclass

from src.draft.flow import DraftState, OffenseRoster
from src.rankings.defense import DefenseOption


@dataclass
class QuarterResult:
    """Points scored in one quarter."""

    quarter: int
    offense_points: int
    defense_points: int
    highlight: str


@dataclass
class GameResult:
    """Full simulated game output."""

    offense_score: int
    defense_score: int
    quarters: list[QuarterResult]
    mvp: str
    winner: str


def _offense_rating(offense: OffenseRoster) -> float:
    """Compute a composite offensive rating from draft picks."""
    total = 0.0
    weights = [
        (offense.qb, 0.30),
        (offense.rb, 0.15),
        (offense.wr1, 0.15),
        (offense.wr2, 0.10),
        (offense.te, 0.10),
    ]
    for player, weight in weights:
        if player:
            total += weight * player.score
    if offense.oline:
        total += 0.20 * offense.oline.score
    return total


def _defense_rating(defense: DefenseOption, scheme: str | None) -> float:
    """Compute a composite defensive rating."""
    base = defense.score
    if scheme == "3-4":
        base += 50  # slight run-stopping bonus
    elif scheme == "4-3":
        base += 30  # slight pass-rush bonus
    return base


def _pick_highlight(offense: OffenseRoster, yards: int, touchdown: bool) -> str:
    """Generate a short highlight line using drafted player names."""
    candidates = [offense.qb, offense.wr1, offense.wr2, offense.rb, offense.te]
    candidates = [p for p in candidates if p is not None]
    player = random.choice(candidates)
    play_type = "TOUCHDOWN" if touchdown else f"{yards}-yard gain"
    return f"  {player.player_name} ({player.team}) — {play_type}"


def simulate_game(state: DraftState) -> GameResult:
    """Simulate quarter-by-quarter scoring and return results."""
    if state.defense is None:
        raise ValueError("Defense must be selected before simulation.")

    offense = state.offense
    defense = state.defense
    off_rating = _offense_rating(offense)
    def_rating = _defense_rating(defense, state.defense_scheme)
    rating_diff = (off_rating - def_rating) / max(abs(off_rating), 1)

    offense_score = 0
    defense_score = 0
    quarters: list[QuarterResult] = []

    for quarter in range(1, 5):
        # Offense drives: rating diff shifts expected points
        base_off = 3 + max(0, int(rating_diff * 8))
        off_points = max(0, base_off + random.randint(-3, 7))

        # Defense can score occasionally (turnover TD / safety flavor)
        def_points = random.randint(0, 3) if random.random() < 0.15 else 0

        touchdown = off_points >= 7
        yards = random.randint(15, 65)
        highlight = _pick_highlight(offense, yards, touchdown)

        offense_score += off_points
        defense_score += def_points
        quarters.append(
            QuarterResult(
                quarter=quarter,
                offense_points=off_points,
                defense_points=def_points,
                highlight=highlight,
            )
        )

    # Pick MVP from highest-scoring offensive pick
    players = [offense.qb, offense.rb, offense.wr1, offense.wr2, offense.te]
    players = [p for p in players if p is not None]
    mvp_player = max(players, key=lambda p: p.score)
    mvp = f"{mvp_player.player_name} ({mvp_player.team})"

    if offense_score > defense_score:
        winner = "Offense"
    elif defense_score > offense_score:
        winner = "Defense"
    else:
        winner = "Tie"

    return GameResult(
        offense_score=offense_score,
        defense_score=defense_score,
        quarters=quarters,
        mvp=mvp,
        winner=winner,
    )


def print_game_result(state: DraftState, result: GameResult) -> None:
    """Print simulation output to the console."""
    print()
    print("=" * 60)
    print("GAME SIMULATION")
    print("=" * 60)
    print(f"\nOffense ({state.season}) vs {state.defense.team} Defense")
    print()

    for q in result.quarters:
        print(f"Q{q.quarter}: Offense +{q.offense_points}", end="")
        if q.defense_points:
            print(f", Defense +{q.defense_points}", end="")
        print()
        print(q.highlight)

    print()
    print(f"FINAL: Offense {result.offense_score} — Defense {result.defense_score}")
    print(f"Winner: {result.winner}")
    print(f"Game MVP: {result.mvp}")
