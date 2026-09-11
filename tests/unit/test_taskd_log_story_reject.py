"""TASK1.8 log story — pull branch reachability=down at WARNING."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from deploy.entourage.taskd import pull_snapshot
from tests.support.log_story import assert_log_story


@pytest.mark.unit
@pytest.mark.log_story
def test_taskd_pull_log_story_reachability_down(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Missing path logs WARNING beat branch with reachability=down.

    :param tmp_path: Isolated dir. Example: ``Path("/tmp/pytest-...")``
    :param caplog: pytest log capture
    :return: None
    """
    caplog.set_level(logging.WARNING)
    pull_snapshot(tmp_path / "gone" / "snapshot.json")
    assert_log_story(
        caplog,
        [{"where": "taskd.pull", "beat": "branch", "must_include": ["reachability=down"], "level": "WARNING"}],
    )
