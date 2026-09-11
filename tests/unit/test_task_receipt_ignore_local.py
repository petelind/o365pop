"""TASK1.7 — untagged Entourage tasks do not queue Graph receipts."""

from __future__ import annotations

from pathlib import Path

import pytest

from deploy.entourage.receipts import queue_receipts
from deploy.entourage.snapshot import parse_snapshot
from deploy.entourage.uid_map import UidMap
from tests.support.fake_entourage import FakeEntourage


@pytest.mark.unit
def test_untagged_local_task_does_not_queue_receipt(tmp_path: Path) -> None:
    """Buy milk without o365pop-uid stays local.

    :param tmp_path: Isolated dir. Example: ``Path("/tmp/pytest-...")``
    :return: None
    """
    entourage = FakeEntourage()
    entourage.create_task({"name": "Buy milk", "content": "grocery list"})
    snapshot = parse_snapshot({"lists": [], "categories": [], "tasks": []})
    queued = queue_receipts(entourage, UidMap(), snapshot, tmp_path / "receipts")
    assert queued == 0
    assert list((tmp_path / "receipts" / "new").glob("*.json")) == []
