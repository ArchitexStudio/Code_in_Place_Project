"""Rank offensive lines by team using team-level stats."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from src.config import TOP_N_PLAYERS
from src.data_loader import first_present, load_team_season_stats, team_column


@dataclass(frozen=True)
class OLineOption:
    """A selectable offensive line (team unit) for a season."""

    team: str
    season: int
    score: float
    stat_line: str
    sacks_suffered: float
    rushing_yards: float


def rank_offensive_lines(season: int, limit: int = TOP_N_PLAYERS) -> list[OLineOption]:
    """
    Rank O-lines by rushing production and sacks allowed.

    Higher rush yards and fewer sacks suffered produce a better score.
    """
    team_stats = load_team_season_stats(season)
    team_col = team_column(team_stats)

    sacks = first_present(team_stats, ["sacks_suffered", "sacks"])
    rush_yards = first_present(team_stats, ["rushing_yards", "rush_yards"])

    ranked = (
        team_stats.with_columns(
            [
                sacks.alias("sacks_suffered_val"),
                rush_yards.alias("rushing_yards_val"),
            ]
        )
        .with_columns(
            (
                pl.col("rushing_yards_val")
                - 20 * pl.col("sacks_suffered_val")
            ).alias("ol_score")
        )
        .sort("ol_score", descending=True)
    )

    options: list[OLineOption] = []
    for row in ranked.iter_rows(named=True):
        sacks_val = float(row.get("sacks_suffered_val") or 0)
        rush_val = float(row.get("rushing_yards_val") or 0)
        score = float(row.get("ol_score") or 0)
        options.append(
            OLineOption(
                team=str(row[team_col]),
                season=season,
                score=score,
                stat_line=f"{int(rush_val)} rush yds, {int(sacks_val)} sacks allowed",
                sacks_suffered=sacks_val,
                rushing_yards=rush_val,
            )
        )

    return options[:limit]
