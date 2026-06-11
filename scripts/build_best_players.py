#!/usr/bin/env python3
"""Build best players by team (1999–latest) from nflverse weekly stats."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import nflreadpy as nfl  # noqa: E402

from src.config import SEASON_MIN  # noqa: E402
from src.data_loader import configure_nflreadpy, player_name_column, team_column  # noqa: E402

POSITIONS = ("QB", "RB", "WR", "TE")
TOP_N = {"QB": 5, "RB": 5, "WR": 8, "TE": 5}

FRANCHISE_ABBR = {
    "STL": "LAR",
    "OAK": "LV",
    "SD": "LAC",
    "LA": "LAR",
    "JAC": "JAX",
    "WSH": "WAS",
}

START_WEEK = {
    "QB": ("attempts", 14),
    "RB": ("carries", 7),
    "WR": ("targets", 5),
    "TE": ("targets", 4),
}

SEASON_START = {
    "QB": 150,
    "RB": 80,
    "WR": 50,
    "TE": 35,
}

CAREER_MIN = {
    "QB": {"attempts": 300, "starts": 8},
    "RB": {"carries": 250, "rush_yds": 800},
    "WR": {"receptions": 150, "rec_yds": 1200},
    "TE": {"receptions": 100, "rec_yds": 800},
}


@dataclass
class PlayerCareer:
    player_id: str
    name: str
    position: str
    team_abbr: str
    team_full: str
    seasons: set[int] = field(default_factory=set)
    reg_starts: int = 0
    post_games: int = 0
    completions: int = 0
    attempts: int = 0
    passing_yards: int = 0
    passing_tds: int = 0
    passing_interceptions: int = 0
    carries: int = 0
    rushing_yards: int = 0
    rushing_tds: int = 0
    receptions: int = 0
    targets: int = 0
    receiving_yards: int = 0
    receiving_tds: int = 0
    season_peaks: list[str] = field(default_factory=list)

    def score(self) -> float:
        pos = self.position
        if pos == "QB":
            return (
                self.passing_yards
                + 25 * self.passing_tds
                - 10 * self.passing_interceptions
                + 0.5 * self.rushing_yards
                + 25 * self.rushing_tds
            )
        if pos == "RB":
            return (
                self.rushing_yards
                + 25 * self.rushing_tds
                + 0.5 * self.receiving_yards
                + 25 * self.receiving_tds
            )
        return self.receiving_yards + 25 * self.receiving_tds

    def qualifies(self) -> bool:
        mins = CAREER_MIN[self.position]
        if self.position == "QB":
            return self.attempts >= mins["attempts"] or self.reg_starts >= mins["starts"]
        if self.position == "RB":
            return self.carries >= mins["carries"] or self.rushing_yards >= mins["rush_yds"]
        if self.position == "WR":
            return self.receptions >= mins["receptions"] or self.receiving_yards >= mins["rec_yds"]
        return self.receptions >= mins["receptions"] or self.receiving_yards >= mins["rec_yds"]


def canonical_abbr(abbr: str) -> str:
    return FRANCHISE_ABBR.get(abbr, abbr)


def passer_rating(comp: int, att: int, yds: int, td: int, ints: int) -> float | None:
    if att <= 0:
        return None
    a = max(0.0, min(2.375, ((comp / att) - 0.3) * 5))
    b = max(0.0, min(2.375, ((yds / att) - 3) * 0.25))
    c = max(0.0, min(2.375, (td / att) * 20))
    d = max(0.0, min(2.375, 2.375 - ((ints / att) * 25)))
    return round(((a + b + c + d) / 6) * 100, 1)


def fmt_years(seasons: set[int]) -> str:
    if not seasons:
        return "—"
    ordered = sorted(seasons)
    ranges: list[str] = []
    start = prev = ordered[0]
    for year in ordered[1:]:
        if year == prev + 1:
            prev = year
            continue
        ranges.append(f"{start}–{prev}" if start != prev else str(start))
        start = prev = year
    ranges.append(f"{start}–{prev}" if start != prev else str(start))
    return ", ".join(ranges)


def fmt_num(value: int) -> str:
    return f"{value:,}"


def rushing_line(p: PlayerCareer) -> str:
    if p.carries <= 0 and p.rushing_yards <= 0:
        return "—"
    return f"{fmt_num(p.rushing_yards)} yds, {p.rushing_tds} TD"


def notes_for(p: PlayerCareer) -> str:
    parts: list[str] = []
    if p.season_peaks:
        parts.append("Peak RS seasons: " + "; ".join(p.season_peaks[:3]))
    if p.post_games:
        parts.append(f"{p.post_games} postseason games with team")
    rating = passer_rating(
        p.completions, p.attempts, p.passing_yards, p.passing_tds, p.passing_interceptions
    )
    if rating is not None and p.position == "QB":
        parts.append(f"Career {p.team_full} passer rating {rating}")
    return " · ".join(parts) if parts else "Regular-season totals with team only"


def load_team_names() -> dict[str, str]:
    teams = nfl.load_teams()
    mapping = dict(zip(teams["team_abbr"].to_list(), teams["team_name"].to_list()))
    for old, new in FRANCHISE_ABBR.items():
        if new in mapping and old not in mapping:
            mapping[old] = mapping[new]
    return mapping


def available_seasons(start: int, end: int) -> list[int]:
    seasons: list[int] = []
    for season in range(start, end + 1):
        try:
            nfl.load_player_stats([season], summary_level="week")
            seasons.append(season)
        except Exception:
            continue
    return seasons


def load_all_weekly(seasons: list[int]) -> pl.DataFrame:
    frames: list[pl.DataFrame] = []
    for season in seasons:
        print(f"Loading {season}...", flush=True)
        frame = nfl.load_player_stats([season], summary_level="week")
        frames.append(frame.filter(pl.col("position").is_in(list(POSITIONS))))
    return pl.concat(frames, how="diagonal")


def aggregate_careers(weekly: pl.DataFrame, team_names: dict[str, str]) -> dict[tuple[str, str, str], PlayerCareer]:
    name_col = player_name_column(weekly)
    team_col = team_column(weekly)
    careers: dict[tuple[str, str, str], PlayerCareer] = {}

    for row in weekly.iter_rows(named=True):
        pos = str(row["position"])
        if pos not in POSITIONS:
            continue
        abbr = canonical_abbr(str(row[team_col]))
        team_full = team_names.get(abbr, abbr)
        pid = str(row["player_id"])
        key = (pid, abbr, pos)
        if key not in careers:
            careers[key] = PlayerCareer(
                player_id=pid,
                name=str(row.get(name_col) or row.get("player_name") or pid),
                position=pos,
                team_abbr=abbr,
                team_full=team_full,
            )
        p = careers[key]
        season = int(row["season"])
        stype = str(row.get("season_type") or "REG")
        p.seasons.add(season)

        stat_col, threshold = START_WEEK[pos]
        week_val = int(row.get(stat_col) or 0)
        if stype == "REG" and week_val >= threshold:
            p.reg_starts += 1
        if stype == "POST" and week_val >= max(1, threshold // 2):
            p.post_games += 1

        for col, attr in (
            ("completions", "completions"),
            ("attempts", "attempts"),
            ("passing_yards", "passing_yards"),
            ("passing_tds", "passing_tds"),
            ("passing_interceptions", "passing_interceptions"),
            ("carries", "carries"),
            ("rushing_yards", "rushing_yards"),
            ("rushing_tds", "rushing_tds"),
            ("receptions", "receptions"),
            ("targets", "targets"),
            ("receiving_yards", "receiving_yards"),
            ("receiving_tds", "receiving_tds"),
        ):
            if col in row and stype == "REG":
                setattr(p, attr, getattr(p, attr) + int(row.get(col) or 0))

    # Season peaks (REG only, per player-team-season)
    season_rows = (
        weekly.filter(pl.col("season_type") == "REG")
        .group_by(["player_id", team_col, "position", "season"])
        .agg(
            [
                pl.col(name_col).first().alias("name"),
                pl.col("attempts").sum(),
                pl.col("passing_yards").sum(),
                pl.col("passing_tds").sum(),
                pl.col("carries").sum(),
                pl.col("rushing_yards").sum(),
                pl.col("receptions").sum(),
                pl.col("receiving_yards").sum(),
            ]
        )
    )
    for row in season_rows.iter_rows(named=True):
        pos = str(row["position"])
        abbr = canonical_abbr(str(row[team_col]))
        pid = str(row["player_id"])
        key = (pid, abbr, pos)
        if key not in careers:
            continue
        p = careers[key]
        season = int(row["season"])
        if pos == "QB" and int(row["attempts"] or 0) >= SEASON_START["QB"]:
            p.season_peaks.append(
                f"{season}: {int(row['passing_yards'] or 0):,} pass yds, {int(row['passing_tds'] or 0)} TD"
            )
        elif pos == "RB" and int(row["carries"] or 0) >= SEASON_START["RB"]:
            p.season_peaks.append(
                f"{season}: {int(row['rushing_yards'] or 0):,} rush yds, {int(row['carries'] or 0)} carries"
            )
        elif pos in {"WR", "TE"} and int(row["receptions"] or 0) >= SEASON_START[pos]:
            p.season_peaks.append(
                f"{season}: {int(row['receiving_yards'] or 0):,} rec yds, {int(row['receptions'] or 0)} rec"
            )

    return careers


def qb_row(rank: int, p: PlayerCareer) -> str:
    comp_pct = (100 * p.completions / p.attempts) if p.attempts else 0
    rating = passer_rating(
        p.completions, p.attempts, p.passing_yards, p.passing_tds, p.passing_interceptions
    )
    return (
        f"| {rank} | {p.name} | {fmt_years(p.seasons)} | {p.reg_starts} | "
        f"{fmt_num(p.passing_yards)} | {p.passing_tds} | {p.passing_interceptions} | "
        f"{comp_pct:.1f}% | {rating if rating is not None else '—'} | "
        f"{rushing_line(p)} | {p.post_games} playoff games | {notes_for(p)} |"
    )


def skill_row(rank: int, p: PlayerCareer) -> str:
    if p.position == "RB":
        stats = f"{fmt_num(p.rushing_yards)} rush yds, {p.rushing_tds} TD"
        extra = f"{p.carries} carries"
        rush = rushing_line(p)
        recv = f"{fmt_num(p.receiving_yards)} rec yds, {p.receiving_tds} TD ({p.receptions} rec)"
    else:
        stats = f"{fmt_num(p.receiving_yards)} rec yds, {p.receiving_tds} TD"
        extra = f"{p.receptions} rec, {p.targets} targets"
        rush = rushing_line(p) if p.carries else "—"
        recv = stats
    return (
        f"| {rank} | {p.name} | {fmt_years(p.seasons)} | {p.reg_starts} | "
        f"{stats} | {extra} | {rush} | {p.post_games} playoff games | {notes_for(p)} |"
    )


def render_markdown(by_team: dict[str, dict[str, list[PlayerCareer]]], season_min: int, season_max: int) -> str:
    lines = [
        f"# Best NFL Players by Team ({season_min}–{season_max})",
        "",
        "Team-specific regular-season totals only. Each player appears once per team with combined stats "
        "from every season he was a meaningful starter for that franchise. Backups with minimal starts are excluded.",
        "",
        "Data source: [nflverse](https://nflverse.nflverse.com/) via nflreadpy. "
        "Games started estimated from weekly usage thresholds. Passer rating computed from aggregated attempts. "
        "2026 included when nflverse publishes that season.",
        "",
    ]
    pos_titles = {
        "QB": "Quarterbacks",
        "RB": "Running Backs",
        "WR": "Wide Receivers",
        "TE": "Tight Ends",
    }
    for team in sorted(by_team):
        lines.extend([f"## Team: {team}", ""])
        for pos in POSITIONS:
            players = by_team[team].get(pos, [])
            lines.append(f"### {pos_titles[pos]}")
            lines.append("")
            if pos == "QB":
                lines.append(
                    "| Rank | Quarterback | Years With Team | Games Started | Passing Yards | "
                    "Passing TDs | INTs | Completion % | Passer Rating | Rushing Stats | "
                    "Playoff Record | Notes |"
                )
                lines.append(
                    "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |"
                )
                for idx, p in enumerate(players, start=1):
                    lines.append(qb_row(idx, p))
            else:
                lines.append(
                    "| Rank | Player | Years With Team | Games Started | Production | "
                    "Volume | Rushing Stats | Playoff Record | Notes |"
                )
                lines.append(
                    "| ---: | --- | --- | ---: | --- | --- | --- | --- | --- |"
                )
                for idx, p in enumerate(players, start=1):
                    lines.append(skill_row(idx, p))
            if not players:
                lines.append("| — | No qualifying starters | — | — | — | — | — | — | — |")
            lines.append("")
    return "\n".join(lines)


def build_best_players(start: int, end: int) -> tuple[dict, str, int, int]:
    configure_nflreadpy()
    seasons = available_seasons(start, end)
    if not seasons:
        raise RuntimeError("No seasons available in nflverse for requested range.")
    team_names = load_team_names()
    weekly = load_all_weekly(seasons)
    careers = aggregate_careers(weekly, team_names)

    by_team: dict[str, dict[str, list[PlayerCareer]]] = {}
    for p in careers.values():
        if not p.qualifies():
            continue
        by_team.setdefault(p.team_full, {}).setdefault(p.position, []).append(p)

    for team in by_team:
        for pos in POSITIONS:
            players = by_team[team].get(pos, [])
            players.sort(key=lambda item: item.score(), reverse=True)
            by_team[team][pos] = players[: TOP_N[pos]]

    season_min, season_max = min(seasons), max(seasons)
    markdown = render_markdown(by_team, season_min, season_max)

    json_payload = {
        "meta": {
            "season_min": season_min,
            "season_max": season_max,
            "source": "nflreadpy / nflverse",
            "positions": list(POSITIONS),
        },
        "teams": {
            team: {
                pos: [
                    {
                        "rank": idx,
                        "name": p.name,
                        "player_id": p.player_id,
                        "years": sorted(p.seasons),
                        "years_label": fmt_years(p.seasons),
                        "games_started": p.reg_starts,
                        "passing_yards": p.passing_yards,
                        "passing_tds": p.passing_tds,
                        "interceptions": p.passing_interceptions,
                        "completion_pct": round(100 * p.completions / p.attempts, 1)
                        if p.attempts
                        else None,
                        "passer_rating": passer_rating(
                            p.completions,
                            p.attempts,
                            p.passing_yards,
                            p.passing_tds,
                            p.passing_interceptions,
                        ),
                        "rushing_yards": p.rushing_yards,
                        "rushing_tds": p.rushing_tds,
                        "receptions": p.receptions,
                        "receiving_yards": p.receiving_yards,
                        "receiving_tds": p.receiving_tds,
                        "postseason_games": p.post_games,
                        "notes": notes_for(p),
                        "score": round(p.score(), 1),
                    }
                    for idx, p in enumerate(by_team[team].get(pos, []), start=1)
                ]
                for pos in POSITIONS
            }
            for team in sorted(by_team)
        },
    }
    return json_payload, markdown, season_min, season_max


def main() -> None:
    parser = argparse.ArgumentParser(description="Build best players by team report")
    parser.add_argument("--start", type=int, default=SEASON_MIN)
    parser.add_argument("--end", type=int, default=2026)
    parser.add_argument(
        "--md-output",
        type=Path,
        default=PROJECT_ROOT / "docs" / "best_players_by_team.md",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=PROJECT_ROOT / "docs" / "best_players_by_team.json",
    )
    args = parser.parse_args()

    payload, markdown, season_min, season_max = build_best_players(args.start, args.end)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.write_text(markdown, encoding="utf-8")
    args.json_output.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(
        f"Wrote {args.md_output} and {args.json_output} "
        f"({season_min}–{season_max}, {len(payload['teams'])} teams)"
    )


if __name__ == "__main__":
    main()
