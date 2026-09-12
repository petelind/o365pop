"""TASK1.8 — missing snapshot does not raise and leaves Entourage alone."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from deploy.entourage.taskd import pull_calendar_snapshot, pull_snapshot, run_calendar_once
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


@pytest.mark.unit
def test_missing_calendar_snapshot_does_not_raise(tmp_path: Path) -> None:
    """CAL1.8: calendar path missing returns unreachable, no exception.

    :param tmp_path: Isolated dir. Example: ``Path("/tmp/pytest-...")``
    :return: None
    """
    entourage = FakeEntourage()
    result = run_calendar_once(tmp_path / "missing" / "snapshot.json", tmp_path, entourage)
    assert result["status"] == "unreachable"
    assert pull_calendar_snapshot(tmp_path / "also-missing.json") is None


@pytest.mark.unit
def test_taskd_module_does_not_import_osascript() -> None:
    """make test must not load OsascriptEntourage.

    :return: None
    """
    code = (
        "import sys\nimport deploy.entourage.taskd\nassert 'deploy.entourage.osascript_entourage' not in sys.modules\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
