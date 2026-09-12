"""TASK — Entourage Project is ``project list``, not ``project``."""

from __future__ import annotations

import pytest

from deploy.entourage.apply import apply_snapshot, backfill_projects
from deploy.entourage.osascript_entourage import _project_assign, _task_assigns, _task_create_script
from deploy.entourage.snapshot import parse_snapshot
from deploy.entourage.uid_map import UidMap
from tests.support.fake_entourage import FakeEntourage


@pytest.mark.unit
def test_task_create_script_sets_project_list() -> None:
    """Create script assigns the Graph list's Project.

    :return: None
    """
    script = _task_create_script({"name": "File the Q3 report", "content": "o365pop-uid: task-q3", "project_id": "12"})
    assert "set project list of t to {project id 12}" in script


@pytest.mark.unit
def test_task_assigns_sets_project_list() -> None:
    """Update script assigns Project the same way.

    :return: None
    """
    body = _task_assigns({"project_id": "12"})
    assert "set project list of t to {project id 12}" in body


@pytest.mark.unit
def test_project_assign_skips_missing_id() -> None:
    """No Project line when the list is not joined.

    :return: None
    """
    assert _project_assign({}) == ""
    assert _project_assign({"project_id": None}) == ""


@pytest.mark.unit
def test_backfill_projects_sets_joined_task_project() -> None:
    """Tasks created without a Project pick up the list join.

    :return: None
    """
    entourage = FakeEntourage()
    uid_map = UidMap()
    snapshot = parse_snapshot(
        {
            "lists": [{"id": "list-work", "displayName": "Work"}],
            "categories": [],
            "tasks": [
                {
                    "id": "task-q3",
                    "listId": "list-work",
                    "title": "File the Q3 report",
                    "status": "notStarted",
                    "categories": [],
                }
            ],
        }
    )
    apply_snapshot(snapshot, entourage, uid_map)
    local_id = uid_map.tasks["task-q3"]
    entourage.update_task(local_id, {"project_id": None})
    assigned = backfill_projects(snapshot, entourage, uid_map)
    assert assigned == 1
    task = entourage.list_tasks()[0]
    assert task["project_id"] == uid_map.lists["list-work"]


@pytest.mark.unit
def test_backfill_projects_skips_missing_local_task() -> None:
    """A deleted Entourage id does not abort the rest of the backfill.

    :return: None
    """
    entourage = FakeEntourage()
    uid_map = UidMap()
    uid_map.lists["list-work"] = "10"
    uid_map.tasks["task-gone"] = "999"
    snapshot = parse_snapshot(
        {
            "lists": [{"id": "list-work", "displayName": "Work"}],
            "categories": [],
            "tasks": [
                {
                    "id": "task-gone",
                    "listId": "list-work",
                    "title": "Gone",
                    "status": "notStarted",
                    "categories": [],
                }
            ],
        }
    )
    assert backfill_projects(snapshot, entourage, uid_map) == 0
