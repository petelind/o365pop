"""TASK publish log story — entry lists=/tasks= and exit path=/bytes=."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.tosser.task_snapshot import publish
from tests.support.fixtures import load_graph_case
from tests.support.log_story import assert_log_story


@pytest.mark.unit
@pytest.mark.log_story
def test_publish_log_story_happy(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Publish logs entry counts and exit path/bytes.

    :param tmp_path: Isolated dir. Example: ``Path("/tmp/pytest-...")``
    :param caplog: pytest log capture
    :return: None
    """
    caplog.set_level(logging.INFO)
    dest = tmp_path / "tasks" / "snapshot.json"
    publish(FileGraphAdapter(load_graph_case("TASK1.1-q3-report")), dest)
    assert_log_story(
        caplog,
        where="tosser.task_snapshot.publish",
        beats={"entry": ["lists=", "tasks="], "exit": ["path=", "bytes="]},
    )
