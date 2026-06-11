"""Classify defensive schemes and rank defenses."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

import polars as pl

from src.config import TOP_N_DEFENSES
from src.data_loader import (
    first_present,
    load_season_pbp,
    load_season_schedule,
    load_team_season_stats,
    parse_personnel_dl,
    team_column,
)

Scheme = str  # "3-4", "4-3", or "Hybrid"


@dataclass(frozen=True)
class DefenseOption:
    """A selectable defense for a season."""

    team: str
    season: int
    scheme: Scheme
    score: float
    stat_line: str
    points_allowed: float
    yards_allowed: float
    turnovers: float


def classify_front(dl_count: int | None) -> Scheme:
    """Map DL count to base defensive front."""
    if dl_count == 4:
        return "4-3"
    if dl_count == 3:
        return "3-4"
    return "Hybrid"


def team_schemes_for_season(season: int) -> dict[str, Scheme]:
    """Infer each team's base defensive front from play-by-play personnel."""
    pbp = load_season_pbp(season)
    if "defense_personnel" not in pbp.columns or "defteam" not in pbp.columns:
        return {}

    schemes: dict[str, Scheme] = {}
    teams = pbp.select("defteam").unique().to_series().to_list()

    for team in teams:
        if team is None:
            continue
        team_plays = pbp.filter(pl.col("defteam") == team)
        dl_counts: Counter[int] = Counter()
        for personnel in team_plays.select("defense_personnel").to_series().to_list():
            dl = parse_personnel_dl(personnel)
            if dl is not None:
                dl_counts[dl] += 1
        if not dl_counts:
            schemes[str(team)] = "Hybrid"
        else:
            most_common_dl = dl_counts.most_common(1)[0][0]
            schemes[str(team)] = classify_front(most_common_dl)

    return schemes


def _points_allowed_from_schedule(season: int) -> dict[str, float]:
    """Compute regular-season points allowed per team from schedules."""
    schedule = load_season_schedule(season)
    needed = {"home_team", "away_team", "home_score", "away_score"}
    if not needed.issubset(set(schedule.columns)):
        return {}

    points: dict[str, float] = defaultdict(float)
    for row in schedule.iter_rows(named=True):
        home = row["home_team"]
        away = row["away_team"]
        home_score = row.get("home_score")
        away_score = row.get("away_score")
        if home_score is None or away_score is None:
            continue
        points[str(home)] += float(away_score)
        points[str(away)] += float(home_score)
    return dict(points)


def _yards_allowed_from_pbp(season: int) -> dict[str, float]:
    """Compute total yards allowed per team from play-by-play."""
    pbp = load_season_pbp(season)
    if "defteam" not in pbp.columns or "yards_gained" not in pbp.columns:
        return {}

    grouped = (
        pbp.filter(pl.col("defteam").is_not_null())
        .group_by("defteam")
        .agg(pl.col("yards_gained").sum().alias("yards_allowed"))
    )
    return {
        str(row["defteam"]): float(row["yards_allowed"] or 0)
        for row in grouped.iter_rows(named=True)
    }


def _scheme_matches(selected: Scheme, team_scheme: Scheme) -> bool:
    """Return True if a team defense fits the user's scheme choice."""
    if team_scheme == selected:
        return True
    return team_scheme == "Hybrid"


def rank_defenses(
    season: int,
    scheme: Scheme,
    limit: int = TOP_N_DEFENSES,
    *,
    filter_by_scheme: bool = True,
) -> list[DefenseOption]:
    """Return top defenses for a season, optionally filtered by scheme."""
    team_stats = load_team_season_stats(season)
    team_col = team_column(team_stats)
    schemes = team_schemes_for_season(season)
    schedule_points = _points_allowed_from_schedule(season)
    pbp_yards = _yards_allowed_from_pbp(season)

    points_allowed = first_present(
        team_stats,
        ["opponent_points", "points_allowed", "def_points", "points_against"],
    )
    yards_allowed = first_present(
        team_stats,
        ["opponent_yards", "yards_allowed", "def_yards"],
    )
    interceptions = first_present(team_stats, ["def_interceptions", "interceptions"])
    fumbles = first_present(team_stats, ["def_fumbles", "fumble_recovery", "fumbles"])

    ranked = team_stats.with_columns(
        [
            points_allowed.alias("points_allowed_col"),
            yards_allowed.alias("yards_allowed_col"),
            (interceptions + fumbles).alias("turnovers_val"),
        ]
    )

    options: list[DefenseOption] = []
    for row in ranked.iter_rows(named=True):
        team = str(row[team_col])
        team_scheme = schemes.get(team, "Hybrid")
        if filter_by_scheme and not _scheme_matches(scheme, team_scheme):
            continue

        points_val = float(row.get("points_allowed_col") or 0)
        yards_val = float(row.get("yards_allowed_col") or 0)
        if points_val == 0 and team in schedule_points:
            points_val = schedule_points[team]
        if yards_val == 0 and team in pbp_yards:
            yards_val = pbp_yards[team]

        turnovers_val = float(row.get("turnovers_val") or 0)
        score = -points_val - 0.05 * yards_val + 10 * turnovers_val

        options.append(
            DefenseOption(
                team=team,
                season=season,
                scheme=team_scheme,
                score=score,
                stat_line=(
                    f"{int(points_val)} pts allowed, {int(yards_val)} yds allowed, "
                    f"{int(turnovers_val)} TO"
                ),
                points_allowed=points_val,
                yards_allowed=yards_val,
                turnovers=turnovers_val,
            )
        )

    options.sort(key=lambda item: item.score, reverse=True)
    return options[:limit]
