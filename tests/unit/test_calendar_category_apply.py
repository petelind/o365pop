"""CAL1.5 — event categories apply without mutating masterCategories."""

from __future__ import annotations

import pytest

from deploy.entourage.calendar_apply import apply_calendar_snapshot
from deploy.entourage.calendar_snapshot import parse_calendar_snapshot
from deploy.entourage.uid_map import UidMap
from tests.support.fake_entourage import FakeEntourage


@pytest.mark.unit
def test_event_category_applies_without_creating_catalog() -> None:
    """Urgent applies when catalog already has Urgent; no new category rows.

    :return: None
    """
    entourage = FakeEntourage()
    uid_map = UidMap()
    before = len(entourage.list_categories())
    entourage.create_category("Urgent", "orange")
    snapshot = parse_calendar_snapshot(
        {
            "calendars": [{"id": "cal-work", "displayName": "Work"}],
            "events": [
                {
                    "id": "evt-standup",
                    "calendarId": "cal-work",
                    "subject": "Standup",
                    "start": {"dateTime": "2026-09-12T13:00:00Z", "timeZone": "UTC"},
                    "end": {"dateTime": "2026-09-12T13:30:00Z", "timeZone": "UTC"},
                    "categories": ["Urgent"],
                }
            ],
        }
    )
    apply_calendar_snapshot(snapshot, entourage, uid_map)
    event = entourage.list_events()[0]
    assert "Urgent" in event["categories"]
    assert len(entourage.list_categories()) == before + 1
