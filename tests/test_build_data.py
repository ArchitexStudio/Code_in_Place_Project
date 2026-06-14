"""Validation tests for built nfl_data.json structure."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "docs" / "nfl_data.json"


@pytest.fixture(scope="module")
def game_data() -> dict:
    if not DATA_PATH.exists():
        pytest.skip("nfl_data.json not built — run scripts/build_nfl_data.py first")
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_meta_season_range(game_data: dict) -> None:
    meta = game_data["meta"]
    assert meta["season_min"] == 1999
    assert meta["season_max"] == 2025


def test_all_years_have_units(game_data: dict) -> None:
    years = set(range(1999, 2026))
    ol_years = {entry[3] for entry in game_data["ol_units"]}
    def_years = {entry[3] for entry in game_data["defense_units"]}
    assert years.issubset(ol_years)
    assert years.issubset(def_years)


def test_defense_units_include_real_stats(game_data: dict) -> None:
    sample = game_data["defense_units"][0]
    assert len(sample) >= 10
    points, yards, takeaways = sample[7], sample[8], sample[9]
    assert isinstance(points, int) and points >= 0
    assert isinstance(yards, int) and yards >= 0
    assert isinstance(takeaways, int) and takeaways >= 0


def test_divisions_cover_32_teams(game_data: dict) -> None:
    divisions = game_data.get("divisions", [])
    assert divisions
    teams = [team for div in divisions for team in div["teams"]]
    abbrs = {team["abbr"] for team in teams}
    assert len(abbrs) == 32


def test_sample_player_exists(game_data: dict) -> None:
    players = game_data["players"]
    matches = [
        p
        for p in players
        if "Manning" in p[1] and p[2] == "QB" and 2005 in p[7]
    ]
    assert matches, "Expected Peyton Manning 2005 QB entry in player pool"
