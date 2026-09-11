"""TASK — FileGraphAdapter publishes atomic snapshot.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.tosser.task_snapshot import publish
from tests.support.fixtures import load_graph_case


@pytest.mark.integration
def test_publish_task_snapshot_atomic_q3(tmp_path: Path) -> None:
    """TASK1.1 fixture becomes snapshot.json; tmp file is gone.

    :param tmp_path: Isolated dir. Example: ``Path("/tmp/pytest-...")``
    :return: None
    """
    dest = tmp_path / "tasks" / "snapshot.json"
    counts = publish(FileGraphAdapter(load_graph_case("TASK1.1-q3-report")), dest)
    assert dest.is_file()
    assert not dest.with_name("snapshot.json.tmp").exists()
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload["lists"][0]["id"] == "list-work"
    assert payload["lists"][0]["displayName"] == "Work"
    assert payload["tasks"][0]["id"] == "task-q3"
    assert payload["tasks"][0]["listId"] == "list-work"
    assert payload["tasks"][0]["dueDateTime"] == "2026-09-12T21:00:00Z"
    assert payload["categories"][0]["color"] == "preset1"
    assert counts["lists"] == 1
    assert counts["tasks"] == 1
    assert counts["bytes"] == dest.stat().st_size
