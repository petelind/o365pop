"""TASK1.2–1.4 — To Do lists create, rename, and delete joined Projects."""

from __future__ import annotations

import pytest

from deploy.entourage.apply import apply_snapshot
from deploy.entourage.snapshot import parse_snapshot
from deploy.entourage.uid_map import UidMap
from tests.support.fake_entourage import FakeEntourage


def _snapshot(*lists: dict) -> object:
    return parse_snapshot({"lists": list(lists), "categories": [], "tasks": []})


@pytest.mark.unit
def test_missing_list_creates_project() -> None:
    """TASK1.2 Garden list becomes a joined Project.

    :return: None
    """
    entourage = FakeEntourage()
    uid_map = UidMap()
    apply_snapshot(_snapshot({"id": "list-garden", "displayName": "Garden"}), entourage, uid_map)
    projects = entourage.list_projects()
    assert [row["name"] for row in projects] == ["Garden"]
    assert uid_map.lists["list-garden"] == projects[0]["id"]


@pytest.mark.unit
def test_existing_project_name_is_joined() -> None:
    """A local Project with the list name is reused, not duplicated.

    :return: None
    """
    entourage = FakeEntourage()
    existing = entourage.create_project("Tasks")
    uid_map = UidMap()
    apply_snapshot(_snapshot({"id": "list-tasks", "displayName": "Tasks"}), entourage, uid_map)
    projects = entourage.list_projects()
    assert [row["name"] for row in projects] == ["Tasks"]
    assert uid_map.lists["list-tasks"] == existing["id"]


@pytest.mark.unit
def test_renamed_list_renames_joined_project() -> None:
    """TASK1.3 Garden → Yard keeps the Graph join.

    :return: None
    """
    entourage = FakeEntourage()
    uid_map = UidMap()
    apply_snapshot(_snapshot({"id": "list-garden", "displayName": "Garden"}), entourage, uid_map)
    apply_snapshot(_snapshot({"id": "list-garden", "displayName": "Yard"}), entourage, uid_map)
    projects = entourage.list_projects()
    assert len(projects) == 1
    assert projects[0]["name"] == "Yard"
    assert uid_map.lists["list-garden"] == projects[0]["id"]
    assert "Garden" not in [row["name"] for row in projects]


@pytest.mark.unit
def test_deleted_list_deletes_project_even_if_calendar_id_lingers() -> None:
    """TASK1.4: leftover uid_map.calendars entry must not keep the Project.

    :return: None
    """
    entourage = FakeEntourage()
    uid_map = UidMap()
    apply_snapshot(_snapshot({"id": "list-garden", "displayName": "Yard"}), entourage, uid_map)
    project_id = uid_map.lists["list-garden"]
    uid_map.calendars["cal-garden"] = project_id
    apply_snapshot(_snapshot(), entourage, uid_map)
    assert entourage.list_projects() == []
    assert "list-garden" not in uid_map.lists


@pytest.mark.unit
def test_deleted_list_deletes_joined_project_only() -> None:
    """TASK1.4 missing list removes the synced Project, not an unjoined one.

    :return: None
    """
    entourage = FakeEntourage()
    local = entourage.create_project("Local only")
    uid_map = UidMap()
    apply_snapshot(_snapshot({"id": "list-garden", "displayName": "Yard"}), entourage, uid_map)
    apply_snapshot(_snapshot(), entourage, uid_map)
    names = {row["name"] for row in entourage.list_projects()}
    assert names == {"Local only"}
    assert "list-garden" not in uid_map.lists
    assert local["id"] in {row["id"] for row in entourage.list_projects()}
