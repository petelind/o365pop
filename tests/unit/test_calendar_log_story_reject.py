"""CAL1.8 — calendar snapshot pull logs reachability=down on missing path."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from deploy.entourage.taskd import pull_calendar_snapshot
from tests.support.log_story import assert_log_story


@pytest.mark.unit
@pytest.mark.log_story
def test_pull_calendar_snapshot_missing_path_logs_reachability_down(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    """Missing CAL snapshot: WARNING branch, no exception.

    :param caplog: Pytest log capture. Example: ``caplog``
    :param tmp_path: Isolated dir. Example: ``Path("/tmp/pytest-...")``
    :return: None
    """
    caplog.set_level(logging.WARNING)
    result = pull_calendar_snapshot(tmp_path / "missing" / "snapshot.json")
    assert result is None
    assert_log_story(
        caplog,
        [
            {
                "where": "taskd.pull",
                "beat": "branch",
                "must_include": ["reachability=down", "kind=calendar"],
                "level": "WARNING",
            }
        ],
    )
