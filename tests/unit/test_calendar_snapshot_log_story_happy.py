"""CAL publish log story — entry calendars=/events= and exit path=/bytes=."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.tosser.calendar_snapshot import publish
from tests.support.fixtures import load_graph_case
from tests.support.log_story import assert_log_story


@pytest.mark.unit
@pytest.mark.log_story
def test_publish_calendar_log_story_happy(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Publish logs entry counts and exit path/bytes.

    :param tmp_path: Isolated dir. Example: ``Path("/tmp/pytest-...")``
    :param caplog: pytest log capture
    :return: None
    """
    caplog.set_level(logging.INFO)
    dest = tmp_path / "calendar" / "snapshot.json"
    publish(FileGraphAdapter(load_graph_case("CAL1.1-standup")), dest)
    assert_log_story(
        caplog,
        where="tosser.calendar_snapshot.publish",
        beats={"entry": ["calendars=", "events="], "exit": ["path=", "bytes="]},
    )
