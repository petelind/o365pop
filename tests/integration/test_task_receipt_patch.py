"""TASK1.6 — Entourage completed queues a receipt that PATCHes Graph."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from deploy.entourage.receipts import queue_receipts
from deploy.entourage.snapshot import parse_snapshot
from deploy.entourage.taskd import run_once
from deploy.entourage.uid_map import UidMap
from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.tosser.task_snapshot import apply_receipts, publish
from tests.support.fake_entourage import FakeEntourage
from tests.support.fixtures import load_graph_case


@pytest.mark.integration
def test_task_receipt_patch_completed(tmp_path: Path) -> None:
    """Completing the Q3 task records PATCH status=completed on FileGraphAdapter.

    :param tmp_path: Isolated dir. Example: ``Path("/tmp/pytest-...")``
    :return: None
    """
    case = tmp_path / "case"
    shutil.copytree(load_graph_case("TASK1.1-q3-report"), case)
    dest = tmp_path / "tasks" / "snapshot.json"
    graph = FileGraphAdapter(case)
    publish(graph, dest)
    entourage = FakeEntourage()
    run_once(dest, tmp_path / "state", entourage)
    task = entourage.list_tasks()[0]
    entourage.update_task(task["id"], {"completed": True})
    snapshot = parse_snapshot(json.loads(dest.read_text(encoding="utf-8")))
    uid_map = UidMap.load(tmp_path / "state" / "uid_map.json")
    queued = queue_receipts(entourage, uid_map, snapshot, dest.parent / "receipts")
    assert queued == 1
    counts = apply_receipts(graph, dest.parent / "receipts")
    assert counts["patched"] == 1
    patched = json.loads((case / "patched.json").read_text(encoding="utf-8"))
    assert patched[0]["listId"] == "list-work"
    assert patched[0]["taskId"] == "task-q3"
    assert patched[0]["body"]["status"] == "completed"
    assert (dest.parent / "receipts" / "sent" / "task-q3.json").is_file()
