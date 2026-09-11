"""TASK1.8 — missing snapshot does not raise and leaves Entourage alone."""

from __future__ import annotations

from pathlib import Path

import pytest

from deploy.entourage.taskd import pull_snapshot
from tests.support.fake_entourage import FakeEntourage


@pytest.mark.unit
def test_missing_snapshot_does_not_raise_or_mutate(tmp_path: Path) -> None:
    """LibreELEC down: None, no exception, FakeEntourage unchanged.

    :param tmp_path: Isolated dir. Example: ``Path("/tmp/pytest-...")``
    :return: None
    """
    entourage = FakeEntourage()
    sentinel = entourage.create_task({"name": "Buy milk", "content": "local only"})
    before = entourage.list_tasks()
    result = pull_snapshot(tmp_path / "missing" / "snapshot.json")
    assert result is None
    after = entourage.list_tasks()
    assert after == before
    assert after[0]["id"] == sentinel["id"]
    assert after[0]["name"] == "Buy milk"
