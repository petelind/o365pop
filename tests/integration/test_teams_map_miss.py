"""TEAM1.4 — unknown o365pop.local fail-closed."""

from __future__ import annotations

import logging
from email.message import EmailMessage
from typing import Any

import pytest

from o365pop.mailstore.spool import SpoolStore
from o365pop.tosser.outbound_scanner import DEFAULT_RETRY_LIMIT, OutboundScanner
from tests.support.log_story import assert_log_story
from tests.support.mailbox import MailboxSandbox, open_sandbox_db

UNKNOWN_TEAMS_ADDRESS = "teams.unknown@o365pop.local"


class _UnusedGraph:
    """GraphPort stand-in: TEAM1.4 must never call Graph."""

    def list_inbox_messages(self) -> list[dict[str, Any]]:
        return []

    def get_message_mime(self, message_id: str) -> bytes:
        raise AssertionError("TEAM1.4 must not get_message_mime")

    def list_new_chat_messages(self) -> list[dict[str, Any]]:
        return []

    def send_mime(self, rfc822: bytes) -> None:
        raise AssertionError("TEAM1.4 must not send_mime")

    def post_chat_message(self, chat_id: str, text: str) -> None:
        raise AssertionError("TEAM1.4 must not post_chat_message")


def _unknown_teams_rfc822() -> bytes:
    """Outbound RFC822 To an unmapped teams.* address.

    :return: RFC822 bytes. Example: ``b"To: teams.unknown@o365pop.local..."``
    """
    message = EmailMessage()
    message["From"] = "denis@o365pop.local"
    message["To"] = UNKNOWN_TEAMS_ADDRESS
    message["Subject"] = "Orphan reply"
    message.set_content("hello")
    return message.as_bytes()


@pytest.mark.integration
@pytest.mark.log_story
def test_scan_unknown_teams_address_does_not_call_graph(
    sandbox: MailboxSandbox,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """map_miss → failed; Graph unused.

    :return: None
    """
    caplog.set_level(logging.INFO)
    conn = open_sandbox_db(sandbox)
    rfc822 = _unknown_teams_rfc822()
    spool = SpoolStore(sandbox.spool)
    enqueued = spool.enqueue(rfc822)
    scanner = OutboundScanner(conn, spool, _UnusedGraph())

    assert DEFAULT_RETRY_LIMIT == 3
    first = scanner.scan_once()
    assert first == {"sent": 0, "failed": 0}
    retry_files = list((sandbox.spool / "retry").glob("*.eml"))
    assert len(retry_files) == 1
    assert retry_files[0].read_bytes() == rfc822
    assert not enqueued.exists()

    second = scanner.scan_once()
    assert second == {"sent": 0, "failed": 0}
    assert len(list((sandbox.spool / "retry").glob("*.eml"))) == 1

    third = scanner.scan_once()
    assert third == {"sent": 0, "failed": 1}
    failed_files = list((sandbox.spool / "failed").glob("*.eml"))
    assert len(failed_files) == 1
    assert failed_files[0].read_bytes() == rfc822
    assert list((sandbox.spool / "retry").glob("*.eml")) == []
    assert list((sandbox.spool / "sent").glob("*.eml")) == []
    assert_log_story(
        caplog,
        where="OutboundScanner.scan_once",
        beats={"error": ["reason=teams_map_miss"]},
        level="ERROR",
    )
    conn.close()
