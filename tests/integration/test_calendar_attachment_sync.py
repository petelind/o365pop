"""CAL1.9 — inbound attachment file and outbound POST recorded."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from deploy.entourage.calendar_receipts import queue_calendar_receipts
from deploy.entourage.taskd import run_calendar_once
from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.tosser.calendar_snapshot import apply_receipts, publish
from tests.support.fake_entourage import FakeEntourage
from tests.support.fixtures import load_graph_case


@pytest.mark.integration
def test_calendar_attachment_sync_inbound_and_outbound(tmp_path: Path) -> None:
    """Snapshot copies agenda.pdf inbound; local add queues attachment POST.

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
    attachments = event.get("attachments") or []
    assert any(row.get("name") == "agenda.pdf" for row in attachments)
    entourage.add_event_attachment(event["id"], "notes.txt", "text/plain", b"bring insurance")
    att_dir = dest.parent / "receipts" / "new" / "attachments"
    att_dir.mkdir(parents=True)
    sidecar = att_dir / "evt-standup-notes.json"
    sidecar.write_text(
        json.dumps(
            {
                "eventId": "evt-standup",
                "name": "notes.txt",
                "contentType": "text/plain",
                "file": "notes.txt",
            }
        ),
        encoding="utf-8",
    )
    (att_dir / "notes.txt").write_bytes(b"bring insurance")
    counts = apply_receipts(graph, dest.parent / "receipts", dest.parent / "acks")
    assert counts["patched"] == 0
    posted = json.loads((case / "calendar_attachments_posted.json").read_text(encoding="utf-8"))
    assert posted[0]["eventId"] == "evt-standup"
    assert posted[0]["name"] == "notes.txt"
    _ = queue_calendar_receipts  # imported for symmetry with receipt flow docs
