"""TASK1.1 — snapshot task becomes an Entourage Task on FakeEntourage."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pytest

from deploy.entourage.taskd import run_once
from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.tosser.task_snapshot import publish
from tests.support.fake_entourage import FakeEntourage
from tests.support.fixtures import load_graph_case
from tests.support.log_story import assert_log_story


@pytest.mark.integration
@pytest.mark.log_story
def test_task_snapshot_create_q3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Publish TASK1.1 fixture and apply: title, due 17:00 EDT, uid, Project, category.

    :param tmp_path: Isolated dir. Example: ``Path("/tmp/pytest-...")``
    :param monkeypatch: TZ override
    :param caplog: pytest log capture
    :return: None
    """
    caplog.set_level(logging.INFO)
    monkeypatch.setenv("TZ", "America/New_York")
    time.tzset()
    dest = tmp_path / "snapshot.json"
    publish(FileGraphAdapter(load_graph_case("TASK1.1-q3-report")), dest)
    entourage = FakeEntourage()
    result = run_once(dest, tmp_path / "state", entourage)
    assert result["status"] == "ok"
    assert result["created"] == 1
    tasks = entourage.list_tasks()
    assert len(tasks) == 1
    task = tasks[0]
    assert task["name"] == "File the Q3 report"
    assert "o365pop-uid: task-q3" in task["content"]
    assert "Work" in task["categories"]
    project = next(row for row in entourage.list_projects() if row["id"] == task["project_id"])
    assert project["name"] == "Work"
    due = task["due"]
    local = due.astimezone()
    assert (local.year, local.month, local.day, local.hour) == (2026, 9, 12, 17)
    assert_log_story(caplog, where="taskd.apply", beats={"processing": ["uid="], "exit": ["created=1"]})
