"""TEAM1.1 — In-Reply-To → chat post."""

from __future__ import annotations

import json
import logging
from email.message import EmailMessage
from pathlib import Path

import pytest

from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.mailstore.spool import SpoolStore
from o365pop.tosser.index import TossedMessage, record_tossed, upsert_chat_map
from o365pop.tosser.outbound_scanner import OutboundScanner
from tests.support.log_story import assert_log_story
from tests.support.mailbox import MailboxSandbox, open_sandbox_db

TEAMS_MESSAGE_ID = "<teams.mjqxg2a.abc@o365pop.local>"
TEAMS_ADDRESS = "teams.mjqxg2a@o365pop.local"


def _reply_rfc822() -> bytes:
    """Outbound Entourage reply with In-Reply-To the tossed Teams id.

    :return: RFC822 bytes. Example: ``b"In-Reply-To: <teams.mjqxg2a.abc@o365pop.local>..."``
    """
    message = EmailMessage()
    message["From"] = "denis@o365pop.local"
    message["To"] = TEAMS_ADDRESS
    message["Subject"] = "Re: Teams: general"
    message["In-Reply-To"] = TEAMS_MESSAGE_ID
    message.set_content("On it\n\n-----Original Message-----\nShip it\n")
    return message.as_bytes()


@pytest.mark.integration
@pytest.mark.log_story
def test_scan_in_reply_to_posts_chat_not_send_mail(
    sandbox: MailboxSandbox,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """POST chat; no sendMail; route=teams_chat.

    :return: None
    """
    caplog.set_level(logging.INFO)
    conn = open_sandbox_db(sandbox)
    record_tossed(
        conn,
        TossedMessage(
            graph_id="teams-msg-1",
            source="teams",
            message_id=TEAMS_MESSAGE_ID,
            chat_id="19:general",
            uidl="uid-teams-1",
        ),
    )
    upsert_chat_map(conn, "19:general", TEAMS_ADDRESS, "mjqxg2a")
    rfc822 = _reply_rfc822()
    spool = SpoolStore(sandbox.spool)
    enqueued = spool.enqueue(rfc822)
    case_dir = tmp_path / "graph-case"
    case_dir.mkdir()
    counts = OutboundScanner(conn, spool, FileGraphAdapter(case_dir)).scan_once()
    assert counts == {"sent": 1, "failed": 0}
    posted = json.loads((case_dir / "posted.json").read_text())
    assert posted == [{"chat_id": "19:general", "text": "On it"}]
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
