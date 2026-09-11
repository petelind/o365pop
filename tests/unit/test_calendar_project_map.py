"""CAL1.2–1.4 — Outlook calendars create, rename, and shared Project delete rules."""

from __future__ import annotations

import pytest

from deploy.entourage.calendar_apply import apply_calendar_snapshot
from deploy.entourage.calendar_snapshot import parse_calendar_snapshot
from deploy.entourage.uid_map import UidMap
from tests.support.fake_entourage import FakeEntourage


def _calendar_snapshot(*calendars: dict) -> object:
    return parse_calendar_snapshot({"calendars": list(calendars), "events": []})


@pytest.mark.unit
def test_missing_calendar_creates_project() -> None:
    """CAL1.2 Garden calendar becomes a joined Project.

    :return: None
    """
    entourage = FakeEntourage()
    uid_map = UidMap()
    apply_calendar_snapshot(
        _calendar_snapshot({"id": "cal-garden", "displayName": "Garden"}),
        entourage,
        uid_map,
    )
    projects = entourage.list_projects()
    assert [row["name"] for row in projects] == ["Garden"]
    assert uid_map.calendars["cal-garden"] == projects[0]["id"]


@pytest.mark.unit
def test_renamed_calendar_renames_joined_project() -> None:
    """CAL1.3 Garden → Yard keeps the calendar join.

    :return: None
    """
    entourage = FakeEntourage()
    uid_map = UidMap()
    apply_calendar_snapshot(
        _calendar_snapshot({"id": "cal-garden", "displayName": "Garden"}),
        entourage,
        uid_map,
    )
    apply_calendar_snapshot(
        _calendar_snapshot({"id": "cal-garden", "displayName": "Yard"}),
        entourage,
        uid_map,
    )
    projects = entourage.list_projects()
    assert len(projects) == 1
    assert projects[0]["name"] == "Yard"
    assert uid_map.calendars["cal-garden"] == projects[0]["id"]


@pytest.mark.unit
def test_deleted_calendar_keeps_project_when_list_join_remains() -> None:
    """CAL1.4 missing calendar drops join but keeps Project when list still joined.

    :return: None
    """
    entourage = FakeEntourage()
    uid_map = UidMap()
    apply_calendar_snapshot(
        _calendar_snapshot({"id": "cal-garden", "displayName": "Yard"}),
        entourage,
        uid_map,
    )
    project_id = uid_map.calendars["cal-garden"]
    uid_map.lists["list-garden"] = project_id
    apply_calendar_snapshot(_calendar_snapshot(), entourage, uid_map)
    projects = entourage.list_projects()
    assert len(projects) == 1
    assert projects[0]["name"] == "Yard"
    assert uid_map.lists["list-garden"] == project_id
    assert "cal-garden" not in uid_map.calendars
