"""Console draft flow: year spin, offense/defense selection."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from src.config import MAX_RESPINS, SEASON_MAX, SEASON_MIN, TOP_N_PLAYERS
from src.rankings.defense import DefenseOption, rank_defenses
from src.rankings.oline import OLineOption, rank_offensive_lines
from src.rankings.players import PlayerOption, top_players_by_position


@dataclass
class OffenseRoster:
    """User-selected offensive unit."""

    season: int
    qb: PlayerOption | None = None
    rb: PlayerOption | None = None
    wr1: PlayerOption | None = None
    wr2: PlayerOption | None = None
    te: PlayerOption | None = None
    oline: OLineOption | None = None


@dataclass
class DraftState:
    """Tracks year selection and draft picks."""

    season: int
    respins_remaining: int = MAX_RESPINS
    offense: OffenseRoster = field(default_factory=lambda: OffenseRoster(season=2000))
    defense: DefenseOption | None = None
    defense_scheme: str | None = None


def print_header(title: str) -> None:
    """Print a section header."""
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def print_rules() -> None:
    """Print welcome message and rules."""
    print_header("ALL-TIME OFFENSE vs ALL-TIME DEFENSE")
    print("Build a dream offense from real NFL stats (1999-2025).")
    print("Pick top players by position, then face a legendary defense.")
    print()
    print("Rules:")
    print("- You get a random season year with 2 free re-spins.")
    print("- Offense: pick from top 5 at QB, RB, WR (x2), TE, plus best O-line team.")
    print("- Defense: choose 3-4 or 4-3, then pick from top 3 matching defenses.")
    print("- Loading stats may take a moment the first time for a season.")


def _prompt_yes_no(prompt: str) -> bool:
    """Ask a yes/no question until valid input."""
    while True:
        answer = input(f"{prompt} (y/n): ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please enter y or n.")


def _prompt_choice(prompt: str, max_choice: int) -> int:
    """Ask for a numbered menu choice."""
    while True:
        raw = input(f"{prompt} (1-{max_choice}): ").strip()
        if not raw.isdigit():
            print("Please enter a number.")
            continue
        choice = int(raw)
        if 1 <= choice <= max_choice:
            return choice
        print(f"Please enter a number between 1 and {max_choice}.")


def assign_season(state: DraftState) -> None:
    """Assign a random season and offer re-spins."""
    state.season = random.randint(SEASON_MIN, SEASON_MAX)
    state.offense = OffenseRoster(season=state.season)
    state.defense = None
    state.defense_scheme = None

    print_header(f"SEASON YEAR: {state.season}")
    print(f"You have {state.respins_remaining} re-spins remaining.")

    while state.respins_remaining > 0:
        if not _prompt_yes_no(f"Keep {state.season}?"):
            state.respins_remaining -= 1
            state.season = random.randint(SEASON_MIN, SEASON_MAX)
            state.offense = OffenseRoster(season=state.season)
            print(f"\nNew year: {state.season}")
            print(f"Re-spins remaining: {state.respins_remaining}")
        else:
            break

    state.offense.season = state.season
    print(f"\nLocked in season: {state.season}")


def _pick_player(position: str, season: int, exclude: set[str] | None = None) -> PlayerOption:
    """Prompt user to pick a player from the top 5 list."""
    exclude = exclude or set()
    options = top_players_by_position(season, position)
    options = [opt for opt in options if opt.player_id not in exclude]

    if not options:
        raise RuntimeError(f"No {position} options found for {season}.")

    print(f"\nTop {position}s in {season}:")
    for index, option in enumerate(options, start=1):
        print(f"  {index}. {option.player_name} ({option.team}) — {option.stat_line}")

    choice = _prompt_choice(f"Pick your {position}", len(options))
    return options[choice - 1]


def draft_offense(state: DraftState) -> None:
    """Run the offensive draft menus."""
    print_header(f"OFFENSE DRAFT — {state.season}")
    season = state.season

    state.offense.qb = _pick_player("QB", season)
    state.offense.rb = _pick_player("RB", season)
    state.offense.wr1 = _pick_player("WR", season)
    state.offense.wr2 = _pick_player("WR", season, exclude={state.offense.wr1.player_id})
    state.offense.te = _pick_player("TE", season)

    oline_options = rank_offensive_lines(season)
    if not oline_options:
        raise RuntimeError(f"No O-line options found for {season}.")

    print(f"\nTop O-Line units in {season}:")
    for index, option in enumerate(oline_options, start=1):
        print(f"  {index}. {option.team} — {option.stat_line}")

    choice = _prompt_choice("Pick your O-Line team", len(oline_options))
    state.offense.oline = oline_options[choice - 1]

    print("\nYour offense:")
    _print_offense_summary(state.offense)


def _print_offense_summary(offense: OffenseRoster) -> None:
    """Print the selected offensive roster."""
    for label, player in [
        ("QB", offense.qb),
        ("RB", offense.rb),
        ("WR1", offense.wr1),
        ("WR2", offense.wr2),
        ("TE", offense.te),
    ]:
        if player:
            print(f"  {label}: {player.player_name} ({player.team}) — {player.stat_line}")
    if offense.oline:
        print(f"  OL:  {offense.oline.team} — {offense.oline.stat_line}")


def draft_defense(state: DraftState) -> None:
    """Run the defensive draft menus."""
    print_header(f"DEFENSE DRAFT — {state.season}")

    print("\nChoose a defensive scheme:")
    print("  1. 4-3")
    print("  2. 3-4")
    scheme_choice = _prompt_choice("Pick scheme", 2)
    scheme = "4-3" if scheme_choice == 1 else "3-4"
    state.defense_scheme = scheme

    options = rank_defenses(state.season, scheme)
    if not options:
        print(f"No {scheme} defenses found; showing best available units.")
        options = rank_defenses(state.season, scheme, filter_by_scheme=False)

    print(f"\nTop {scheme} defenses in {state.season}:")
    for index, option in enumerate(options, start=1):
        print(
            f"  {index}. {option.team} ({option.scheme}) — {option.stat_line}"
        )

    choice = _prompt_choice("Pick your defense", len(options))
    state.defense = options[choice - 1]

    print(f"\nYour defense: {state.defense.team} ({state.defense.scheme})")


def run_draft() -> DraftState:
    """Run the full draft flow and return final state."""
    state = DraftState(season=SEASON_MIN)
    assign_season(state)
    draft_offense(state)
    draft_defense(state)
    return state
