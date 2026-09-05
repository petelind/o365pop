"""TEAM1.2 — To teams.* without In-Reply-To."""

from __future__ import annotations

import json
import logging
from email.message import EmailMessage
from pathlib import Path

import pytest

from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.mailstore.spool import SpoolStore
from o365pop.tosser.index import upsert_chat_map
from o365pop.tosser.outbound_scanner import OutboundScanner
from tests.support.log_story import assert_log_story
from tests.support.mailbox import MailboxSandbox, open_sandbox_db

TEAMS_ADDRESS = "teams.mjqxg2a@o365pop.local"


def _to_address_rfc822() -> bytes:
    """Outbound RFC822 To the ChatMap address with no In-Reply-To.

    :return: RFC822 bytes. Example: ``b"To: teams.mjqxg2a@o365pop.local..."``
    """
    message = EmailMessage()
    message["From"] = "denis@o365pop.local"
    message["To"] = TEAMS_ADDRESS
    message["Subject"] = "Teams: general"
    message.set_content("Still on it")
    return message.as_bytes()


@pytest.mark.integration
@pytest.mark.log_story
def test_scan_to_teams_address_posts_chat(
    sandbox: MailboxSandbox,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """To teams.mjqxg2a@o365pop.local → chat post.

    :return: None
    """
    caplog.set_level(logging.INFO)
    conn = open_sandbox_db(sandbox)
    upsert_chat_map(conn, "19:general", TEAMS_ADDRESS, "mjqxg2a")
    rfc822 = _to_address_rfc822()
    assert b"In-Reply-To" not in rfc822
    spool = SpoolStore(sandbox.spool)
    enqueued = spool.enqueue(rfc822)
    case_dir = tmp_path / "graph-case"
    case_dir.mkdir()
    counts = OutboundScanner(conn, spool, FileGraphAdapter(case_dir)).scan_once()
    assert counts == {"sent": 1, "failed": 0}
    posted = json.loads((case_dir / "posted.json").read_text())
    assert posted == [{"chat_id": "19:general", "text": "Still on it"}]
    assert not (case_dir / "sent.eml").exists()
    assert not enqueued.exists()
    sent_files = list((sandbox.spool / "sent").glob("*.eml"))
    assert len(sent_files) == 1
    assert sent_files[0].read_bytes() == rfc822
    assert_log_story(
        caplog,
        where="OutboundRouter.route",
        beats={"branch": ["route=teams_chat"]},
    )
    conn.close()
