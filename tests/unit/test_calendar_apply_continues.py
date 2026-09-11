"""Calendar apply must log a bad event and continue the rest of the snapshot."""

from __future__ import annotations

import logging

import pytest

from deploy.entourage.calendar_apply import apply_calendar_snapshot
from deploy.entourage.calendar_snapshot import parse_calendar_snapshot
from deploy.entourage.uid_map import UidMap
from tests.support.fake_entourage import FakeEntourage


class _FailOnSubjectEntourage(FakeEntourage):
    """Create events except one subject that raises like live osascript."""

    def create_event(self, properties: dict) -> dict:
        """Raise on the Zoom-meeting subject, otherwise create.

        :param properties: Event fields. Example: ``{"subject": "Standup"}``
        :return: Created record. Example: ``{"id": "1", "subject": "Standup"}``
        :raises RuntimeError: when subject matches the known live failure
        """
        if "Taming the AI" in str(properties.get("subject") or ""):
            raise RuntimeError("osascript rc=1")
        return super().create_event(properties)


def _two_event_snapshot() -> object:
    return parse_calendar_snapshot(
        {
            "calendars": [{"id": "cal-work", "displayName": "Work"}],
            "events": [
                {
                    "id": "evt-zoom",
                    "calendarId": "cal-work",
                    "subject": "Taming the AI: Knowledge Sharing sessions(part 2)",
                    "start": {"dateTime": "2026-09-11T17:00:00Z", "timeZone": "UTC"},
                    "end": {"dateTime": "2026-09-11T18:00:00Z", "timeZone": "UTC"},
                },
                {
                    "id": "evt-standup",
                    "calendarId": "cal-work",
                    "subject": "Standup",
                    "start": {"dateTime": "2026-09-12T13:00:00Z", "timeZone": "UTC"},
                    "end": {"dateTime": "2026-09-12T13:30:00Z", "timeZone": "UTC"},
                },
            ],
        }
    )


@pytest.mark.unit
def test_apply_continues_after_one_event_osascript_error(caplog: pytest.LogCaptureFixture) -> None:
    """A RuntimeError on event 1 must not prevent event 2 from being created.

    :param caplog: pytest log capture
    :return: None
    """
    caplog.set_level(logging.ERROR)
    entourage = _FailOnSubjectEntourage()
    uid_map = UidMap()
    counts = apply_calendar_snapshot(_two_event_snapshot(), entourage, uid_map)
    subjects = [row["subject"] for row in entourage.list_events()]
    assert subjects == ["Standup"]
    assert "evt-standup" in uid_map.events
    assert "evt-zoom" not in uid_map.events
    assert counts["created"] == 1
    assert counts["failed"] == 1
    assert any("evt-zoom" in rec.getMessage() and "osascript rc=1" in rec.getMessage() for rec in caplog.records)
