"""CAL — FileGraphAdapter publishes atomic calendar/snapshot.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.tosser.calendar_snapshot import publish
from tests.support.fixtures import load_graph_case


@pytest.mark.integration
def test_publish_calendar_snapshot_atomic_standup(tmp_path: Path) -> None:
    """CAL1.1 fixture becomes snapshot.json; tmp file is gone; attachment copied.

    :param tmp_path: Isolated dir. Example: ``Path("/tmp/pytest-...")``
    :return: None
    """
    dest = tmp_path / "calendar" / "snapshot.json"
    counts = publish(FileGraphAdapter(load_graph_case("CAL1.1-standup")), dest)
    assert dest.is_file()
    assert not dest.with_name("snapshot.json.tmp").exists()
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload["calendars"][0]["id"] == "cal-work"
    assert payload["calendars"][0]["displayName"] == "Work"
    assert payload["events"][0]["id"] == "evt-standup"
    assert payload["events"][0]["calendarId"] == "cal-work"
    assert payload["events"][0]["subject"] == "Standup"
    assert payload["events"][0]["location"] == "Room A"
    assert payload["events"][0]["reminderMinutesBeforeStart"] == 15
    assert payload["events"][0]["attendees"][0]["email"] == "ada@contoso.com"
    assert payload["events"][0]["attachments"][0]["name"] == "agenda.pdf"
    attachment_path = tmp_path / "calendar" / "attachments" / "evt-standup" / "agenda.pdf"
    assert attachment_path.is_file()
    assert counts["calendars"] == 1
    assert counts["events"] == 1
    assert counts["bytes"] == dest.stat().st_size
