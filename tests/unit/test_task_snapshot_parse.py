"""TASK — snapshot JSON parse (valid dict; missing id rejected)."""

from __future__ import annotations

import pytest

from deploy.entourage.snapshot import SnapshotError, parse_snapshot


@pytest.mark.unit
def test_parse_snapshot_accepts_q3_fixture_shape() -> None:
    """TASK1.1 contract object becomes typed rows.

    :return: None
    """
    snapshot = parse_snapshot(
        {
            "generated_at": "2026-09-11T16:00:00Z",
            "lists": [{"id": "list-work", "displayName": "Work"}],
            "categories": [{"id": "cat-red", "displayName": "Urgent", "color": "preset1"}],
            "tasks": [
                {
                    "id": "task-q3",
                    "listId": "list-work",
                    "title": "File the Q3 report",
                    "dueDateTime": "2026-09-12T21:00:00Z",
                    "status": "notStarted",
                    "categories": ["Work"],
                    "lastModifiedDateTime": "2026-09-11T15:00:00Z",
                }
            ],
        }
    )
    assert snapshot.lists[0].id == "list-work"
    assert snapshot.lists[0].display_name == "Work"
    assert snapshot.tasks[0].id == "task-q3"
    assert snapshot.tasks[0].title == "File the Q3 report"
    assert snapshot.tasks[0].due_datetime == "2026-09-12T21:00:00Z"
    assert snapshot.categories[0].color == "preset1"


@pytest.mark.unit
def test_parse_snapshot_rejects_task_missing_id() -> None:
    """A task without id is SnapshotError.

    :return: None
    """
    with pytest.raises(SnapshotError, match="task missing id"):
        parse_snapshot({"tasks": [{"title": "orphan"}]})
