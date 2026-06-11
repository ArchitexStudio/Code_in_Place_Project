"""Rank offensive players by position with team-season splits."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from src.config import TOP_N_PLAYERS
from src.data_loader import (
    available_sum_columns,
    load_player_weekly_stats,
    player_name_column,
    team_column,
)


@dataclass(frozen=True)
class PlayerOption:
    """A selectable player entry for one team in one season."""

    player_id: str
    player_name: str
    team: str
    position: str
    season: int
    score: float
    stat_line: str
    stats: dict[str, float]


def _score_for_position(position: str, row: dict[str, float]) -> float:
    """Compute a ranking score based on position-relevant stats."""
    if position == "QB":
        return row.get("passing_yards", 0) + 25 * row.get("passing_tds", 0)
    if position == "RB":
        return row.get("rushing_yards", 0) + 25 * row.get("rushing_tds", 0)
    if position in {"WR", "TE"}:
        return row.get("receiving_yards", 0) + 25 * row.get("receiving_tds", 0)
    return 0.0


def _format_stat_line(position: str, row: dict[str, float]) -> str:
    """Build a short stat summary for menu display."""
    if position == "QB":
        return (
            f"{int(row.get('passing_yards', 0))} pass yds, "
            f"{int(row.get('passing_tds', 0))} TD"
        )
    if position == "RB":
        return (
            f"{int(row.get('rushing_yards', 0))} rush yds, "
            f"{int(row.get('rushing_tds', 0))} TD"
        )
    if position in {"WR", "TE"}:
        return (
            f"{int(row.get('receiving_yards', 0))} rec yds, "
            f"{int(row.get('receiving_tds', 0))} TD"
        )
    return ""


def aggregate_team_season_players(season: int) -> pl.DataFrame:
    """
    Aggregate weekly player stats by player, team, and position.

    Traded players appear once per team they played for that season.
    """
    weekly = load_player_weekly_stats(season)
    team_col = team_column(weekly)
    name_col = player_name_column(weekly)
    sum_cols = available_sum_columns(weekly)

    grouped = (
        weekly.filter(pl.col("season") == season)
        .filter(pl.col("position").is_in(["QB", "RB", "WR", "TE"]))
        .group_by(["player_id", name_col, team_col, "position", "season"])
        .agg([pl.col(col).sum().alias(col) for col in sum_cols])
        .rename({name_col: "player_name", team_col: "team"})
    )
    return grouped


def top_players_by_position(season: int, position: str, limit: int = TOP_N_PLAYERS) -> list[PlayerOption]:
    """Return top N players at a position for a season (team-season entries)."""
    aggregated = aggregate_team_season_players(season)
    position_rows = aggregated.filter(pl.col("position") == position)

    options: list[PlayerOption] = []
    for row in position_rows.iter_rows(named=True):
        stats = {key: float(row.get(key) or 0) for key in available_sum_columns(aggregated)}
        score = _score_for_position(position, stats)
        if score <= 0:
            continue
        options.append(
            PlayerOption(
                player_id=str(row["player_id"]),
                player_name=str(row["player_name"]),
                team=str(row["team"]),
                position=position,
                season=season,
                score=score,
                stat_line=_format_stat_line(position, stats),
                stats=stats,
            )
        )

    options.sort(key=lambda item: item.score, reverse=True)
    return options[:limit]
