"""CAL1.7 — untagged local Entourage event POSTs to Graph then ack stamps uid."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from deploy.entourage.calendar_apply import apply_pending_acks
from deploy.entourage.calendar_receipts import queue_calendar_receipts
from deploy.entourage.calendar_snapshot import parse_calendar_snapshot
from deploy.entourage.taskd import run_calendar_once
from deploy.entourage.uid_map import UidMap
from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.tosser.calendar_snapshot import apply_receipts, publish
from tests.support.fake_entourage import FakeEntourage
from tests.support.fixtures import load_graph_case


@pytest.mark.integration
def test_calendar_receipt_create_dentist(tmp_path: Path) -> None:
    """Untagged Dentist event POSTs to cal-work and ack stamps o365pop-uid.

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
    project_id = entourage.list_projects()[0]["id"]
    dentist = entourage.create_event(
        {
            "subject": "Dentist",
            "start": datetime(2026, 9, 15, 18, 0, tzinfo=timezone.utc),
            "end": datetime(2026, 9, 15, 19, 0, tzinfo=timezone.utc),
            "project_id": project_id,
            "content": "",
            "to_recipients": [],
        }
    )
    snapshot = parse_calendar_snapshot(json.loads(dest.read_text(encoding="utf-8")))
    uid_map = UidMap.load(tmp_path / "state" / "uid_map.json")
    queued = queue_calendar_receipts(entourage, uid_map, snapshot, dest.parent / "receipts")
    assert queued == 1
    counts = apply_receipts(graph, dest.parent / "receipts", dest.parent / "acks")
    assert counts["created"] == 1
    created = json.loads((case / "created_events.json").read_text(encoding="utf-8"))
    assert created[0]["calendarId"] == "cal-work"
    assert created[0]["subject"] == "Dentist"
    ack_path = dest.parent / "acks" / f"{dentist['id']}.json"
    assert ack_path.is_file()
    apply_pending_acks(dest.parent / "acks", entourage, uid_map)
    content = entourage.get_event_content(dentist["id"])
    assert "o365pop-uid: evt-created-1" in content
