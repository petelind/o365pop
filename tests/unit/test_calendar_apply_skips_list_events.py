"""Joined event updates must not dump the whole Entourage calendar."""

from __future__ import annotations

import pytest

from deploy.entourage.calendar_apply import apply_calendar_snapshot
from deploy.entourage.calendar_snapshot import parse_calendar_snapshot
from deploy.entourage.uid_map import UidMap
from tests.support.fake_entourage import FakeEntourage


def _event(event_id: str, subject: str) -> dict:
    return {
        "id": event_id,
        "calendarId": "cal-work",
        "subject": subject,
        "start": {"dateTime": "2026-09-12T13:00:00Z", "timeZone": "UTC"},
        "end": {"dateTime": "2026-09-12T13:30:00Z", "timeZone": "UTC"},
    }


@pytest.mark.unit
def test_joined_event_update_does_not_list_all_events() -> None:
    """Live list_events dumps content of every event and times out at 120s per joined row.

    :return: None
    """
    snapshot = parse_calendar_snapshot(
        {
            "calendars": [{"id": "cal-work", "displayName": "Work"}],
            "events": [
                _event("evt-a", "Standup moved"),
                _event("evt-b", "Retro"),
                _event("evt-c", "1:1"),
                _event("evt-new", "New leftover"),
            ],
        }
    )
    entourage = FakeEntourage()
    uid_map = UidMap()
    uid_map.calendars["cal-work"] = str(entourage.create_project({"name": "Work"})["id"])
    for graph_id, subject in (("evt-a", "Standup"), ("evt-b", "Retro"), ("evt-c", "1:1")):
        created = entourage.create_event({"subject": subject})
        uid_map.events[graph_id] = str(created["id"])
    entourage.list_events_calls = 0

    counts = apply_calendar_snapshot(snapshot, entourage, uid_map)

    assert entourage.list_events_calls == 0
    assert counts["created"] == 1
    assert counts["updated"] == 3
    assert counts["failed"] == 0
    assert "evt-new" in uid_map.events
    subjects = {row["subject"] for row in entourage.list_events()}
    assert "Standup moved" in subjects
    assert "New leftover" in subjects
