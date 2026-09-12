"""CAL1.2–1.4 — event category creates a Project; calendar name does not."""

from __future__ import annotations

import logging

import pytest

from deploy.entourage.calendar_apply import apply_calendar_snapshot
from deploy.entourage.calendar_snapshot import parse_calendar_snapshot
from deploy.entourage.uid_map import UidMap
from tests.support.fake_entourage import FakeEntourage
from tests.support.log_story import assert_log_story


def _snapshot(calendars: list[dict], events: list[dict]) -> object:
    return parse_calendar_snapshot({"calendars": calendars, "events": events})


def _event(event_id: str, subject: str, categories: list[str] | None = None) -> dict:
    row = {
        "id": event_id,
        "calendarId": "cal-work",
        "subject": subject,
        "start": {"dateTime": "2026-09-12T13:00:00Z", "timeZone": "UTC"},
        "end": {"dateTime": "2026-09-12T13:30:00Z", "timeZone": "UTC"},
    }
    if categories is not None:
        row["categories"] = categories
    return row


@pytest.mark.unit
def test_event_category_creates_project(caplog: pytest.LogCaptureFixture) -> None:
    """CAL1.2 Garden category becomes a Project; Calendar does not.

    :param caplog: pytest log capture
    :return: None
    """
    caplog.set_level(logging.INFO)
    entourage = FakeEntourage()
    uid_map = UidMap()
    apply_calendar_snapshot(
        _snapshot(
            [{"id": "cal-work", "displayName": "Calendar", "isDefault": True}],
            [_event("evt-standup", "Standup", ["Garden"])],
        ),
        entourage,
        uid_map,
    )
    projects = entourage.list_projects()
    assert [row["name"] for row in projects] == ["Garden"]
    event = entourage.list_events()[0]
    assert event["project_id"] == projects[0]["id"]
    assert_log_story(
        caplog,
        where="taskd.apply",
        beats={"branch": ["project_from_category=true", "name=Garden"], "exit": ["created=1"]},
    )


@pytest.mark.unit
def test_uncategorized_event_has_no_project(caplog: pytest.LogCaptureFixture) -> None:
    """CAL1.3 uncategorized event stays Calendar-only.

    :param caplog: pytest log capture
    :return: None
    """
    caplog.set_level(logging.INFO)
    entourage = FakeEntourage()
    uid_map = UidMap()
    apply_calendar_snapshot(
        _snapshot(
            [{"id": "cal-work", "displayName": "Calendar", "isDefault": True}],
            [_event("evt-dentist", "Dentist", [])],
        ),
        entourage,
        uid_map,
    )
    assert entourage.list_projects() == []
    event = entourage.list_events()[0]
    assert event.get("project_id") in (None, "")
    assert_log_story(
        caplog,
        where="taskd.apply",
        beats={"branch": ["uncategorized=true", "uid=evt-dentist"]},
    )


@pytest.mark.unit
def test_calendar_display_name_does_not_create_or_rename_project(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CAL1.4 calendar rename must not mint or rename a Project.

    :param caplog: pytest log capture
    :return: None
    """
    caplog.set_level(logging.INFO)
    entourage = FakeEntourage()
    uid_map = UidMap()
    first = _snapshot(
        [{"id": "cal-work", "displayName": "Calendar", "isDefault": True}],
        [_event("evt-standup", "Standup", ["Work"])],
    )
    apply_calendar_snapshot(first, entourage, uid_map)
    apply_calendar_snapshot(
        _snapshot(
            [{"id": "cal-work", "displayName": "Mailbox", "isDefault": True}],
            [_event("evt-standup", "Standup", ["Work"])],
        ),
        entourage,
        uid_map,
    )
    names = [row["name"] for row in entourage.list_projects()]
    assert names == ["Work"]
    assert_log_story(caplog, where="taskd.apply", beats={"branch": ["calendar_is_not_project=true", "name=Mailbox"]})
