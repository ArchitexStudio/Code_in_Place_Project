"""Unit tests for ranking and draft logic."""

from __future__ import annotations

import polars as pl
import pytest

from src.config import MAX_RESPINS, TOP_N_PLAYERS
from src.data_loader import parse_personnel_dl
from src.draft.flow import DraftState
from src.rankings.defense import classify_front, rank_defenses, team_schemes_for_season
from src.rankings.oline import rank_offensive_lines
from src.rankings.players import (
    PlayerOption,
    _score_for_position,
    aggregate_team_season_players,
    top_players_by_position,
)
from src.simulation.game import _defense_rating, _offense_rating, simulate_game
from src.draft.flow import OffenseRoster


class TestHelpers:
    def test_parse_personnel_dl(self):
        assert parse_personnel_dl("4 DL, 3 LB, 4 DB") == 4
        assert parse_personnel_dl("3 DL, 4 LB, 4 DB") == 3
        assert parse_personnel_dl(None) is None
        assert parse_personnel_dl("invalid") is None

    def test_classify_front(self):
        assert classify_front(4) == "4-3"
        assert classify_front(3) == "3-4"
        assert classify_front(5) == "Hybrid"

    def test_score_for_position(self):
        qb_stats = {"passing_yards": 4000, "passing_tds": 30}
        assert _score_for_position("QB", qb_stats) == 4000 + 25 * 30

        rb_stats = {"rushing_yards": 1200, "rushing_tds": 10}
        assert _score_for_position("RB", rb_stats) == 1200 + 250


class TestPlayerRankings:
    @pytest.fixture
    def weekly_stats(self):
        return pl.DataFrame(
            {
                "player_id": ["p1", "p1", "p2", "p3"],
                "player_display_name": ["Tom Brady", "Tom Brady", "LaDainian Tomlinson", "Randy Moss"],
                "team": ["NE", "NE", "SD", "NE"],
                "position": ["QB", "QB", "RB", "WR"],
                "season": [2007, 2007, 2007, 2007],
                "week": [1, 2, 1, 1],
                "passing_yards": [300, 350, 0, 0],
                "passing_tds": [2, 3, 0, 0],
                "rushing_yards": [0, 0, 120, 0],
                "rushing_tds": [0, 0, 1, 0],
                "receiving_yards": [0, 0, 0, 150],
                "receiving_tds": [0, 0, 0, 2],
            }
        )

    def test_aggregate_team_season_players(self, weekly_stats, monkeypatch):
        monkeypatch.setattr(
            "src.rankings.players.load_player_weekly_stats",
            lambda season: weekly_stats,
        )
        result = aggregate_team_season_players(2007)
        assert len(result) == 3
        brady = result.filter(pl.col("player_name") == "Tom Brady")
        assert brady["passing_yards"][0] == 650

    def test_top_players_returns_at_most_five(self, weekly_stats, monkeypatch):
        monkeypatch.setattr(
            "src.rankings.players.load_player_weekly_stats",
            lambda season: weekly_stats,
        )
        qbs = top_players_by_position(2007, "QB")
        assert len(qbs) <= TOP_N_PLAYERS
        assert qbs[0].player_name == "Tom Brady"


class TestTeamRankings:
    @pytest.fixture
    def team_stats(self):
        return pl.DataFrame(
            {
                "team": ["NE", "DAL", "SF"],
                "season": [2007, 2007, 2007],
                "sacks_suffered": [20, 30, 15],
                "rushing_yards": [1800, 1600, 2000],
            }
        )

    def test_rank_offensive_lines(self, team_stats, monkeypatch):
        monkeypatch.setattr(
            "src.rankings.oline.load_team_season_stats",
            lambda season: team_stats,
        )
        lines = rank_offensive_lines(2007)
        assert len(lines) <= TOP_N_PLAYERS
        assert lines[0].team == "SF"

    def test_rank_defenses_with_schedule_fallback(self, monkeypatch):
        team_stats = pl.DataFrame(
            {
                "team": ["NE", "NYG", "DAL"],
                "season": [2007, 2007, 2007],
            }
        )
        schedule = pl.DataFrame(
            {
                "home_team": ["NE", "NYG"],
                "away_team": ["NYG", "DAL"],
                "home_score": [14, 21],
                "away_score": [10, 17],
            }
        )
        pbp = pl.DataFrame(
            {
                "defteam": ["NE", "NE", "NYG"],
                "defense_personnel": ["4 DL, 3 LB, 4 DB", "4 DL, 3 LB, 4 DB", "3 DL, 4 LB, 4 DB"],
                "yards_gained": [5, 10, 20],
            }
        )

        monkeypatch.setattr(
            "src.rankings.defense.load_team_season_stats",
            lambda season: team_stats,
        )
        monkeypatch.setattr(
            "src.rankings.defense.load_season_schedule",
            lambda season: schedule,
        )
        monkeypatch.setattr(
            "src.rankings.defense.load_season_pbp",
            lambda season: pbp,
        )

        schemes = team_schemes_for_season(2007)
        assert schemes["NE"] == "4-3"
        assert schemes["NYG"] == "3-4"

        defenses = rank_defenses(2007, "4-3")
        assert len(defenses) <= 3
        assert all(d.scheme in {"4-3", "Hybrid"} for d in defenses)


class TestDraftState:
    def test_respins_default(self):
        state = DraftState(season=2007)
        assert state.respins_remaining == MAX_RESPINS


class TestSimulation:
    def test_simulation_produces_scores(self):
        offense = OffenseRoster(
            season=2007,
            qb=PlayerOption("1", "QB Player", "NE", "QB", 2007, 5000, "stats", {}),
            rb=PlayerOption("2", "RB Player", "NE", "RB", 2007, 2000, "stats", {}),
            wr1=PlayerOption("3", "WR1", "NE", "WR", 2007, 1500, "stats", {}),
            wr2=PlayerOption("4", "WR2", "NE", "WR", 2007, 1200, "stats", {}),
            te=PlayerOption("5", "TE", "NE", "TE", 2007, 800, "stats", {}),
        )
        from src.rankings.defense import DefenseOption

        state = DraftState(season=2007)
        state.offense = offense
        state.defense_scheme = "4-3"
        state.defense = DefenseOption(
            team="NYG",
            season=2007,
            scheme="4-3",
            score=100,
            stat_line="test",
            points_allowed=250,
            yards_allowed=5000,
            turnovers=20,
        )

        assert _offense_rating(offense) > 0
        assert _defense_rating(state.defense, "4-3") > 0

        result = simulate_game(state)
        assert result.offense_score >= 0
        assert len(result.quarters) == 4
        assert result.mvp
