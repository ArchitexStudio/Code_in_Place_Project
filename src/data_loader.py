"""Load NFL data from nflreadpy with caching."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import polars as pl

from src.config import CACHE_DIR, PLAYER_SUM_COLUMNS

_configured = False


def configure_nflreadpy() -> None:
    """Configure nflreadpy once per process."""
    global _configured
    if _configured:
        return

    from nflreadpy.config import update_config

    # nflreadpy calls cache_dir.mkdir(); setattr bypasses pydantic Path coercion.
    cache_dir = Path(CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    update_config(
        cache_mode="filesystem",
        cache_dir=cache_dir,
        cache_duration=86400,
        verbose=False,
        timeout=60,
    )
    _configured = True


def _import_nfl():
    configure_nflreadpy()
    import nflreadpy as nfl

    return nfl


@lru_cache(maxsize=8)
def load_player_weekly_stats(season: int) -> pl.DataFrame:
    """Load weekly player stats for a single season."""
    nfl = _import_nfl()
    return nfl.load_player_stats([season], summary_level="week")


@lru_cache(maxsize=8)
def load_team_season_stats(season: int) -> pl.DataFrame:
    """Load regular-season team stats for a single season."""
    nfl = _import_nfl()
    return nfl.load_team_stats([season], summary_level="reg")


@lru_cache(maxsize=4)
def load_season_pbp(season: int) -> pl.DataFrame:
    """Load play-by-play data for scheme classification."""
    nfl = _import_nfl()
    return nfl.load_pbp([season])


@lru_cache(maxsize=8)
def load_season_schedule(season: int) -> pl.DataFrame:
    """Load game schedules and results for a season."""
    nfl = _import_nfl()
    return nfl.load_schedules([season])


def team_column(frame: pl.DataFrame) -> str:
    """Return the team column name present in a frame."""
    for name in ("team", "recent_team"):
        if name in frame.columns:
            return name
    raise ValueError("No team column found in data frame.")


def player_name_column(frame: pl.DataFrame) -> str:
    """Return the best available player name column."""
    for name in ("player_display_name", "player_name"):
        if name in frame.columns:
            return name
    raise ValueError("No player name column found in data frame.")


def available_sum_columns(frame: pl.DataFrame) -> list[str]:
    """Return stat columns that exist and can be summed."""
    return [col for col in PLAYER_SUM_COLUMNS if col in frame.columns]


def parse_personnel_dl(personnel: str | None) -> int | None:
    """Extract DL count from defense personnel string."""
    if not personnel:
        return None
    match = re.search(r"(\d+)\s*DL", str(personnel))
    if not match:
        return None
    return int(match.group(1))


def first_present(frame: pl.DataFrame, candidates: list[str], default: float = 0.0) -> pl.Expr:
    """Use the first candidate column that exists, else a literal default."""
    for name in candidates:
        if name in frame.columns:
            return pl.col(name).fill_null(default)
    return pl.lit(default)
