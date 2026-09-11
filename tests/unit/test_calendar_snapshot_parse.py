"""CAL — calendar snapshot JSON parse (valid dict; missing id rejected)."""

from __future__ import annotations

import pytest

from deploy.entourage.calendar_snapshot import CalendarSnapshotError, parse_calendar_snapshot


@pytest.mark.unit
def test_parse_calendar_snapshot_accepts_standup_fixture_shape() -> None:
    """CAL1.1 contract object becomes typed rows.

    :return: None
    """
    snapshot = parse_calendar_snapshot(
        {
            "generated_at": "2026-09-11T16:00:00Z",
            "window": {"start": "2026-08-12T00:00:00Z", "end": "2027-03-10T00:00:00Z"},
            "calendars": [{"id": "cal-work", "displayName": "Work", "isDefault": False}],
            "events": [
                {
                    "id": "evt-standup",
                    "calendarId": "cal-work",
                    "subject": "Standup",
                    "start": {"dateTime": "2026-09-12T13:00:00Z", "timeZone": "UTC"},
                    "end": {"dateTime": "2026-09-12T13:30:00Z", "timeZone": "UTC"},
                    "isAllDay": False,
                    "location": "Room A",
                    "bodyPreview": "Daily",
                    "categories": ["Work"],
                    "attendees": [{"name": "Ada Lovelace", "email": "ada@contoso.com", "type": "required"}],
                    "showAs": "busy",
                    "sensitivity": "normal",
                    "reminderMinutesBeforeStart": 15,
                    "lastModifiedDateTime": "2026-09-11T15:00:00Z",
                    "attachments": [{"name": "agenda.pdf", "contentType": "application/pdf"}],
                }
            ],
        }
    )
    assert snapshot.calendars[0].id == "cal-work"
    assert snapshot.calendars[0].display_name == "Work"
    assert snapshot.events[0].id == "evt-standup"
    assert snapshot.events[0].subject == "Standup"
    assert snapshot.events[0].reminder_minutes == 15
    assert snapshot.events[0].attendees[0].email == "ada@contoso.com"
    assert snapshot.events[0].attachments[0].name == "agenda.pdf"


@pytest.mark.unit
def test_parse_calendar_snapshot_rejects_event_missing_id() -> None:
    """An event without id is CalendarSnapshotError.

    :return: None
    """
    with pytest.raises(CalendarSnapshotError, match="event missing id"):
        parse_calendar_snapshot({"events": [{"subject": "orphan"}]})
