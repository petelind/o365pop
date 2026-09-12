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
def test_uncategorized_event_clears_stale_calendar_project(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CAL1.3 leftover Project Calendar is cleared off the event, then deleted.

    :param caplog: pytest log capture
    :return: None
    """
    caplog.set_level(logging.INFO)
    entourage = FakeEntourage()
    leftover = entourage.create_project("Calendar")
    stale = entourage.create_event({"subject": "Focus time", "project_id": leftover["id"]})
    uid_map = UidMap()
    uid_map.events["evt-focus"] = stale["id"]
    apply_calendar_snapshot(
        _snapshot(
            [{"id": "cal-work", "displayName": "Calendar", "isDefault": True}],
            [_event("evt-focus", "Focus time", [])],
        ),
        entourage,
        uid_map,
    )
    event = entourage.list_events()[0]
    assert event.get("project_id") in (None, "")
    assert "Calendar" not in {row["name"] for row in entourage.list_projects()}
    assert_log_story(
        caplog,
        [
            {
                "where": "taskd.apply",
                "beat": "branch",
                "must_include": ["uncategorized=true", "uid=evt-focus"],
            },
            {
                "where": "taskd.apply",
                "beat": "branch",
                "must_include": ["leftover_calendar_removed=true", "name=Calendar"],
            },
        ],
    )


@pytest.mark.unit
def test_leftover_calendar_project_deleted_after_category_move(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Categorized events leave Project Calendar; the leftover Project is deleted.

    :param caplog: pytest log capture
    :return: None
    """
    caplog.set_level(logging.INFO)
    entourage = FakeEntourage()
    leftover = entourage.create_project("Calendar")
    stale = entourage.create_event({"subject": "Standup", "project_id": leftover["id"]})
    uid_map = UidMap()
    uid_map.events["evt-standup"] = stale["id"]
    apply_calendar_snapshot(
        _snapshot(
            [{"id": "cal-work", "displayName": "Calendar", "isDefault": True}],
            [_event("evt-standup", "Standup", ["Garden"])],
        ),
        entourage,
        uid_map,
    )
    names = [row["name"] for row in entourage.list_projects()]
    assert names == ["Garden"]
    event = entourage.list_events()[0]
    assert event["project_id"] == entourage.list_projects()[0]["id"]
    assert_log_story(
        caplog,
        where="taskd.apply",
        beats={"branch": ["leftover_calendar_removed=true", "name=Calendar"]},
    )


@pytest.mark.unit
def test_calendar_project_kept_when_todo_list_joins_it() -> None:
    """A To Do list named Calendar must not be deleted by the calendar hop.

    :return: None
    """
    entourage = FakeEntourage()
    leftover = entourage.create_project("Calendar")
    uid_map = UidMap()
    uid_map.lists["list-calendar"] = leftover["id"]
    apply_calendar_snapshot(
        _snapshot(
            [{"id": "cal-work", "displayName": "Calendar", "isDefault": True}],
            [_event("evt-standup", "Standup", ["Work"])],
        ),
        entourage,
        uid_map,
    )
    names = {row["name"] for row in entourage.list_projects()}
    assert names == {"Calendar", "Work"}


@pytest.mark.unit
def test_calendar_project_kept_when_event_category_is_calendar() -> None:
    """Category name Calendar is a real Project, not the leftover mailbox name.

    :return: None
    """
    entourage = FakeEntourage()
    apply_calendar_snapshot(
        _snapshot(
            [{"id": "cal-work", "displayName": "Calendar", "isDefault": True}],
            [_event("evt-standup", "Standup", ["Calendar"])],
        ),
        entourage,
        UidMap(),
    )
    names = [row["name"] for row in entourage.list_projects()]
    assert names == ["Calendar"]
    event = entourage.list_events()[0]
    assert event["project_id"] == entourage.list_projects()[0]["id"]


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
