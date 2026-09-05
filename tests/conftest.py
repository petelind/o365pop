"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_log_dir(tmp_path: Path) -> Path:
    """Isolated log directory for a single test.

    :param tmp_path: pytest tmp path. Example: ``Path("/tmp/pytest-of-denis/...")``
    :return: ``logs`` subdirectory. Example: ``Path("/tmp/.../logs")``
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Isolated SQLite path for a single test.

    :param tmp_path: pytest tmp path. Example: ``Path("/tmp/pytest-of-denis/...")``
    :return: Database file path (not yet created). Example: ``Path("/tmp/.../data/o365pop.sqlite3")``
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir / "o365pop.sqlite3"
