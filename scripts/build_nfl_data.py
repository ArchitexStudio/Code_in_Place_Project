#!/usr/bin/env python3
"""Build nfl_data.json for the web game from nflreadpy."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import nflreadpy as nfl  # noqa: E402

from src.config import SEASON_MAX, SEASON_MIN  # noqa: E402
from src.data_loader import configure_nflreadpy  # noqa: E402
from src.rankings.defense import rank_defenses, team_schemes_for_season  # noqa: E402
from src.rankings.oline import rank_offensive_lines  # noqa: E402
from src.rankings.players import (  # noqa: E402
    _format_stat_line,
    _score_for_position,
    aggregate_team_season_players,
    available_sum_columns,
)


def era_from_year(year: int) -> str:
    if year < 2010:
        return "2000s"
    if year < 2020:
        return "2010s"
    return "2020s"


def scheme_code(scheme: str) -> str:
    if scheme == "3-4":
        return "34"
    return "43"


def score_to_rating(score: float, max_score: float) -> int:
    if max_score <= 0:
        return 85
    ratio = score / max_score
    return min(99, max(80, int(80 + ratio * 19)))


def load_team_names() -> dict[str, str]:
    teams = nfl.load_teams()
    return dict(zip(teams["team_abbr"].to_list(), teams["team_name"].to_list()))


def build_players(season: int, team_names: dict[str, str]) -> list[list]:
    """Build player entries for one season (all rostered players per team-position)."""
    aggregated = aggregate_team_season_players(season)
    sum_cols = available_sum_columns(aggregated)
    entries: list[list] = []

    for position in ("QB", "RB", "WR", "TE"):
        pos_rows = aggregated.filter(aggregated["position"] == position)
        if pos_rows.is_empty():
            continue

        scored: list[tuple[float, dict]] = []
        for row in pos_rows.iter_rows(named=True):
            stats = {key: float(row.get(key) or 0) for key in sum_cols}
            score = _score_for_position(position, stats)
            if score <= 0:
                continue
            scored.append((score, row))

        if not scored:
            continue

        max_score = max(s for s, _ in scored)
        by_team: dict[str, list[tuple[float, dict]]] = {}
        for score, row in scored:
            team = str(row["team"])
            by_team.setdefault(team, []).append((score, row))

        for team, team_rows in by_team.items():
            team_rows.sort(key=lambda item: item[0], reverse=True)
            for score, row in team_rows:
                team_full = team_names.get(team, team)
                player_id = f"{row['player_id']}|{team}|{season}"
                name = str(row["player_name"])
                rating = score_to_rating(score, max_score)
                stat = _format_stat_line(position, {k: float(row.get(k) or 0) for k in sum_cols})
                stat_line = f"{team} RS only: {stat} ({season} regular season)"
                entries.append(
                    [
                        player_id,
                        name,
                        position,
                        team_full,
                        era_from_year(season),
                        rating,
                        stat_line,
                        [season],
                    ]
                )

    return entries


def build_ol_units(season: int, team_names: dict[str, str]) -> list[list]:
    lines = rank_offensive_lines(season, limit=3)
    units: list[list] = []
    for idx, line in enumerate(lines, start=1):
        team_abbr = line.team
        team_full = team_names.get(team_abbr, team_abbr)
        units.append(
            [
                f"{season} {team_full} OL",
                team_full,
                era_from_year(season),
                season,
                score_to_rating(line.score, lines[0].score if lines else line.score),
                f"Year top {idx} seed · {line.stat_line} · regular season only",
            ]
        )
    return units


def build_def_units(season: int, team_names: dict[str, str]) -> list[list]:
    schemes = team_schemes_for_season(season)
    all_defs = rank_defenses(season, "4-3", limit=32, filter_by_scheme=False)
    top = all_defs[:3]
    units: list[list] = []
    for idx, defense in enumerate(top, start=1):
        team_abbr = defense.team
        team_full = team_names.get(team_abbr, team_abbr)
        scheme = schemes.get(team_abbr, defense.scheme)
        units.append(
            [
                f"{season} {team_full} Defense",
                team_full,
                era_from_year(season),
                season,
                score_to_rating(defense.score, top[0].score if top else defense.score),
                scheme_code(scheme),
                f"Year top {idx} seed · {defense.stat_line} · regular season only",
            ]
        )
    return units


def build_data(seasons: list[int]) -> dict:
    configure_nflreadpy()
    team_names = load_team_names()
    teams = sorted(set(team_names.values()))

    players: list[list] = []
    ol_units: list[list] = []
    defense_units: list[list] = []

    for season in seasons:
        print(f"Building {season}...", flush=True)
        players.extend(build_players(season, team_names))
        ol_units.extend(build_ol_units(season, team_names))
        defense_units.extend(build_def_units(season, team_names))

    return {
        "teams": teams,
        "unit_years": seasons,
        "players": players,
        "ol_units": ol_units,
        "defense_units": defense_units,
        "meta": {
            "season_min": min(seasons),
            "season_max": max(seasons),
            "source": "nflreadpy / nflverse",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build web game NFL data JSON")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "docs" / "nfl_data.json",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=SEASON_MIN,
    )
    parser.add_argument(
        "--end",
        type=int,
        default=SEASON_MAX,
    )
    args = parser.parse_args()
    seasons = list(range(args.start, args.end + 1))

    data = build_data(seasons)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, separators=(",", ":"))
    data["meta"]["cache_key"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    payload = json.dumps(data, separators=(",", ":"))
    args.output.write_text(payload, encoding="utf-8")
    gzip_path = args.output.with_suffix(".json.gz")
    gzip_path.write_bytes(gzip.compress(payload.encode("utf-8"), compresslevel=9))

    print(
        f"Wrote {args.output} ({len(payload)} bytes) "
        f"and {gzip_path} ({gzip_path.stat().st_size} bytes) "
        f"— {len(data['players'])} players, "
        f"{len(data['ol_units'])} OL units, "
        f"{len(data['defense_units'])} defenses"
    )


if __name__ == "__main__":
    main()
