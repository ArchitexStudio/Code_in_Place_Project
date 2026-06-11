"""Tests for nflreadpy configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
from nflreadpy.config import get_config, reset_config, update_config


@pytest.fixture(autouse=True)
def _reset_nflreadpy_config():
    reset_config()
    yield
    reset_config()


def test_configure_nflreadpy_uses_path_cache_dir(monkeypatch: pytest.MonkeyPatch):
    """cache_dir must stay a Path; nflreadpy calls .mkdir() on it."""
    from src.data_loader import configure_nflreadpy

    monkeypatch.setattr("src.data_loader._configured", False)
    configure_nflreadpy()

    cache_dir = get_config().cache_dir
    assert isinstance(cache_dir, Path)
    assert cache_dir.exists()


def test_str_cache_dir_breaks_nflreadpy_mkdir():
    """Document nflreadpy bug: str cache_dir raises on first filesystem cache use."""
    update_config(cache_mode="filesystem", cache_dir=".cache/nflreadpy-test")
    cache_dir = get_config().cache_dir
    assert isinstance(cache_dir, str)
    with pytest.raises(AttributeError, match="mkdir"):
        cache_dir.mkdir(parents=True, exist_ok=True)
