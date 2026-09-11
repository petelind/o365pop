"""CAL1.6 — Entourage edit queues a receipt that PATCHes Graph without attendees."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from deploy.entourage.calendar_receipts import queue_calendar_receipts
from deploy.entourage.calendar_snapshot import parse_calendar_snapshot
from deploy.entourage.taskd import run_calendar_once
from deploy.entourage.uid_map import UidMap
from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.tosser.calendar_snapshot import apply_receipts, publish
from tests.support.fake_entourage import FakeEntourage
from tests.support.fixtures import load_graph_case


@pytest.mark.integration
def test_calendar_receipt_patch_standup_moved(tmp_path: Path) -> None:
    """Editing subject/location/reminder/show-as/sensitivity records PATCH without attendees.

    :param tmp_path: Isolated dir. Example: ``Path("/tmp/pytest-...")``
    :return: None
    """
    case = tmp_path / "case"
    shutil.copytree(load_graph_case("CAL1.1-standup"), case)
    dest = tmp_path / "calendar" / "snapshot.json"
    graph = FileGraphAdapter(case)
    publish(graph, dest)
    entourage = FakeEntourage()
    run_calendar_once(dest, tmp_path / "state", entourage)
    event = entourage.list_events()[0]
    entourage.update_event(
        event["id"],
        {
            "subject": "Standup moved",
            "location": "Room B",
            "reminder_minutes": 10,
            "show_as": "tentative",
            "sensitivity": "private",
        },
    )
    snapshot = parse_calendar_snapshot(json.loads(dest.read_text(encoding="utf-8")))
    uid_map = UidMap.load(tmp_path / "state" / "uid_map.json")
    queued = queue_calendar_receipts(entourage, uid_map, snapshot, dest.parent / "receipts")
    assert queued == 1
    counts = apply_receipts(graph, dest.parent / "receipts", dest.parent / "acks")
    assert counts["patched"] == 1
    patched = json.loads((case / "calendar_patched.json").read_text(encoding="utf-8"))
    assert patched[0]["eventId"] == "evt-standup"
    body = patched[0]["body"]
    assert body["subject"] == "Standup moved"
    assert body["location"] == "Room B"
    assert body["reminderMinutesBeforeStart"] == 10
    assert body["showAs"] == "tentative"
    assert body["sensitivity"] == "private"
    assert "attendees" not in body
    assert (dest.parent / "receipts" / "sent" / "evt-standup.json").is_file()
