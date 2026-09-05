"""TEAM1.3 — ordinary To still sendMail."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.mailstore.spool import SpoolStore
from o365pop.tosser.outbound_scanner import OutboundScanner
from tests.support.fixtures import load_mail
from tests.support.log_story import assert_log_story
from tests.support.mailbox import MailboxSandbox, open_sandbox_db


@pytest.mark.integration
@pytest.mark.log_story
def test_scan_ordinary_recipient_still_send_mail(
    sandbox: MailboxSandbox,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """ada@example.com → sendMail; no chat POST.

    :return: None
    """
    caplog.set_level(logging.INFO)
    conn = open_sandbox_db(sandbox)
    rfc822 = load_mail("hello-ada")
    spool = SpoolStore(sandbox.spool)
    enqueued = spool.enqueue(rfc822)
    case_dir = tmp_path / "graph-case"
    case_dir.mkdir()
    counts = OutboundScanner(conn, spool, FileGraphAdapter(case_dir)).scan_once()
    assert counts == {"sent": 1, "failed": 0}
    assert (case_dir / "sent.eml").read_bytes() == rfc822
    assert not (case_dir / "posted.json").exists()
    assert not enqueued.exists()
    sent_files = list((sandbox.spool / "sent").glob("*.eml"))
    assert len(sent_files) == 1
    assert sent_files[0].read_bytes() == rfc822
    assert list((sandbox.spool / "new").glob("*.eml")) == []
    assert_log_story(
        caplog,
        where="OutboundScanner.scan_once",
        beats={"exit": ["sent=1"]},
    )
    conn.close()
