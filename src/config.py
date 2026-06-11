"""Project configuration constants."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / ".cache" / "nflreadpy"

SEASON_MIN = 1999
SEASON_MAX = 2025
MAX_RESPINS = 2
TOP_N_PLAYERS = 5
TOP_N_DEFENSES = 3

OFFENSE_POSITIONS = ["QB", "RB", "WR", "TE"]

# Columns summed when aggregating weekly player stats by team.
PLAYER_SUM_COLUMNS = [
    "completions",
    "attempts",
    "passing_yards",
    "passing_tds",
    "passing_interceptions",
    "carries",
    "rushing_yards",
    "rushing_tds",
    "receptions",
    "targets",
    "receiving_yards",
    "receiving_tds",
]
