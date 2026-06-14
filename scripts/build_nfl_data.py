#!/usr/bin/env python3
"""Build nfl_data.json for the web game from nflreadpy."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import nflreadpy as nfl  # noqa: E402

from src.config import FRANCHISE_ABBR, SEASON_MAX, SEASON_MIN  # noqa: E402
from src.data_loader import configure_nflreadpy, load_season_schedule  # noqa: E402
from src.rankings.defense import rank_defenses, team_schemes_for_season  # noqa: E402
from src.rankings.oline import rank_offensive_lines  # noqa: E402
from src.rankings.players import (  # noqa: E402
    _format_stat_line,
    _score_for_position,
    aggregate_team_season_players,
    available_sum_columns,
)

DIVISION_ORDER = {
    ("AFC", "AFC East"): 0,
    ("AFC", "AFC North"): 1,
    ("AFC", "AFC South"): 2,
    ("AFC", "AFC West"): 3,
    ("NFC", "NFC East"): 4,
    ("NFC", "NFC North"): 5,
    ("NFC", "NFC South"): 6,
    ("NFC", "NFC West"): 7,
}


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


def canonical_abbr(abbr: str) -> str:
    return FRANCHISE_ABBR.get(abbr, abbr)


def score_to_rating(score: float, max_score: float) -> int:
    if max_score <= 0:
        return 85
    ratio = score / max_score
    return min(99, max(80, int(80 + ratio * 19)))


def load_team_names() -> dict[str, str]:
    teams = nfl.load_teams()
    names: dict[str, str] = {}
    for row in teams.iter_rows(named=True):
        abbr = canonical_abbr(str(row["team_abbr"]))
        names[abbr] = str(row["team_name"])
    return names


def build_divisions(team_names: dict[str, str], win_rates: dict[str, float]) -> list[dict]:
    teams = nfl.load_teams()
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in teams.iter_rows(named=True):
        abbr = canonical_abbr(str(row["team_abbr"]))
        conf = str(row.get("team_conf") or "")
        division = str(row.get("team_division") or "")
        name = team_names.get(abbr, str(row["team_name"]))
        win_rate = win_rates.get(abbr, 0.5)
        # Higher win rate = easier schedule tint (greener); lower = harder (redder).
        difficulty = max(0.15, min(0.85, 1.0 - win_rate))
        groups[(conf, division)].append(
            {
                "abbr": abbr,
                "name": name,
                "difficulty": round(difficulty, 3),
            }
        )
    ordered = sorted(groups.items(), key=lambda item: DIVISION_ORDER.get(item[0], 99))
    return [
        {
            "conf": conf,
            "div": div.replace("AFC ", "").replace("NFC ", ""),
            "label": div,
            "teams": sorted(teams_list, key=lambda t: t["abbr"]),
        }
        for (conf, div), teams_list in ordered
    ]


def compute_win_rates(seasons: list[int]) -> dict[str, float]:
    wins: dict[str, float] = defaultdict(float)
    games: dict[str, float] = defaultdict(float)
    for season in seasons:
        schedule = load_season_schedule(season)
        needed = {"home_team", "away_team", "home_score", "away_score"}
        if not needed.issubset(set(schedule.columns)):
            continue
        for row in schedule.iter_rows(named=True):
            home = canonical_abbr(str(row["home_team"]))
            away = canonical_abbr(str(row["away_team"]))
            home_score = row.get("home_score")
            away_score = row.get("away_score")
            if home_score is None or away_score is None:
                continue
            games[home] += 1
            games[away] += 1
            if float(home_score) > float(away_score):
                wins[home] += 1
            elif float(away_score) > float(home_score):
                wins[away] += 1
            else:
                wins[home] += 0.5
                wins[away] += 0.5
    return {team: wins[team] / games[team] for team in games if games[team] > 0}


def build_players_combined(seasons: list[int], team_names: dict[str, str]) -> list[list]:
    """One entry per player×team with combined REG stats across all stints (1999–2025)."""
    careers: dict[tuple[str, str, str], dict] = {}
    sum_cols: list[str] | None = None

    for season in seasons:
        print(f"  Players {season}...", flush=True)
        aggregated = aggregate_team_season_players(season)
        cols = available_sum_columns(aggregated)
        if sum_cols is None:
            sum_cols = cols

        for row in aggregated.iter_rows(named=True):
            position = str(row["position"])
            if position not in ("QB", "RB", "WR", "TE"):
                continue
            team = canonical_abbr(str(row["team"]))
            pid = str(row["player_id"])
            key = (pid, team, position)
            if key not in careers:
                careers[key] = {
                    "player_id": pid,
                    "name": str(row["player_name"]),
                    "team": team,
                    "position": position,
                    "stats": {col: 0.0 for col in cols},
                    "seasons": set(),
                }
            bucket = careers[key]
            for col in cols:
                bucket["stats"][col] += float(row.get(col) or 0)
            bucket["seasons"].add(season)

    if not sum_cols:
        return []

    by_team_pos: dict[tuple[str, str], list[tuple[float, dict]]] = defaultdict(list)
    for bucket in careers.values():
        score = _score_for_position(bucket["position"], bucket["stats"])
        if score <= 0:
            continue
        by_team_pos[(bucket["team"], bucket["position"])].append((score, bucket))

    entries: list[list] = []
    for (team, position), rows in by_team_pos.items():
        max_score = max(s for s, _ in rows)
        team_full = team_names.get(team, team)
        for score, bucket in sorted(rows, key=lambda item: item[0], reverse=True):
            seasons_sorted = sorted(bucket["seasons"])
            years_label = (
                f"{seasons_sorted[0]}–{seasons_sorted[-1]}"
                if len(seasons_sorted) > 1
                else str(seasons_sorted[0])
            )
            stat = _format_stat_line(position, bucket["stats"])
            stat_line = (
                f"{team} RS combined: {stat} ({years_label} regular season"
                f"{'s' if len(seasons_sorted) > 1 else ''})"
            )
            entries.append(
                [
                    f"{bucket['player_id']}|{team}",
                    bucket["name"],
                    position,
                    team_full,
                    era_from_year(seasons_sorted[-1]),
                    score_to_rating(score, max_score),
                    stat_line,
                    seasons_sorted,
                ]
            )

    return entries


def build_ol_units(season: int, team_names: dict[str, str]) -> list[list]:
    lines = rank_offensive_lines(season, limit=3)
    units: list[list] = []
    for idx, line in enumerate(lines, start=1):
        team_abbr = canonical_abbr(line.team)
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
        team_abbr = canonical_abbr(defense.team)
        team_full = team_names.get(team_abbr, team_abbr)
        scheme = schemes.get(defense.team, defense.scheme)
        units.append(
            [
                f"{season} {team_full} Defense",
                team_full,
                era_from_year(season),
                season,
                score_to_rating(defense.score, top[0].score if top else defense.score),
                scheme_code(scheme),
                f"Year top {idx} seed · {defense.stat_line} · regular season only",
                int(defense.points_allowed),
                int(defense.yards_allowed),
                int(defense.turnovers),
            ]
        )
    return units


def build_data(seasons: list[int]) -> dict:
    configure_nflreadpy()
    team_names = load_team_names()
    teams = sorted(set(team_names.values()))
    win_rates = compute_win_rates(seasons)
    divisions = build_divisions(team_names, win_rates)

    players = build_players_combined(seasons, team_names)
    ol_units: list[list] = []
    defense_units: list[list] = []

    for season in seasons:
        print(f"Building units {season}...", flush=True)
        ol_units.extend(build_ol_units(season, team_names))
        defense_units.extend(build_def_units(season, team_names))

    return {
        "teams": teams,
        "unit_years": seasons,
        "players": players,
        "ol_units": ol_units,
        "defense_units": defense_units,
        "divisions": divisions,
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
