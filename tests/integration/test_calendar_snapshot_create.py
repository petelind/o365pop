"""CAL1.1 — snapshot event becomes an Entourage event on FakeEntourage."""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

import pytest

from deploy.entourage.taskd import run_calendar_once
from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.tosser.calendar_snapshot import publish
from tests.support.fake_entourage import FakeEntourage
from tests.support.fixtures import load_graph_case
from tests.support.log_story import assert_log_story


@pytest.mark.integration
@pytest.mark.log_story
def test_calendar_snapshot_create_standup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Publish CAL1.1 fixture and apply: subject, uid, Project, category, reminder, attendees.

    :param tmp_path: Isolated dir. Example: ``Path("/tmp/pytest-...")``
    :param monkeypatch: TZ override
    :param caplog: pytest log capture
    :return: None
    """
    caplog.set_level(logging.INFO)
    monkeypatch.setenv("TZ", "America/New_York")
    time.tzset()
    case = tmp_path / "case"
    shutil.copytree(load_graph_case("CAL1.1-standup"), case)
    dest = tmp_path / "calendar" / "snapshot.json"
    publish(FileGraphAdapter(case), dest)
    entourage = FakeEntourage()
    result = run_calendar_once(dest, tmp_path / "state", entourage)
    assert result["status"] == "ok"
    assert result["created"] == 1
    events = entourage.list_events()
    assert len(events) == 1
    event = events[0]
    assert event["subject"] == "Standup"
    assert "o365pop-uid: evt-standup" in event["content"]
    assert "Ada Lovelace" in event["content"]
    assert "ada@contoso.com" in event["content"]
    assert "deck" in event["content"]
    assert "<strong>" not in event["content"]
    assert event.get("content_is_html") is not True
    assert event["to_recipients"] == []
    assert "Work" in event["categories"]
    assert event["reminder_minutes"] == 15
    assert event["show_as"] == "busy"
    assert event["sensitivity"] == "normal"
    project = next(row for row in entourage.list_projects() if row["id"] == event["project_id"])
    assert project["name"] == "Work"
    assert "Calendar" not in {row["name"] for row in entourage.list_projects()}
    start = event["start"].astimezone()
    end = event["end"].astimezone()
    assert (start.year, start.month, start.day, start.hour, start.minute) == (2026, 9, 12, 9, 0)
    assert (end.year, end.month, end.day, end.hour, end.minute) == (2026, 9, 12, 9, 30)
    assert_log_story(caplog, where="taskd.apply", beats={"processing": ["uid="], "exit": ["created=1"]})
