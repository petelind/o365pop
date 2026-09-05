"""SEND1.2 — Graph 400 → retry then failed."""

from __future__ import annotations

import logging
from typing import Any

import httpx
import pytest

from o365pop.mailstore.spool import SpoolStore
from o365pop.tosser.outbound_scanner import DEFAULT_RETRY_LIMIT, OutboundScanner
from tests.support.fixtures import load_mail
from tests.support.log_story import assert_log_story
from tests.support.mailbox import MailboxSandbox, open_sandbox_db


class _FailingSendGraph:
    """GraphPort stand-in: sendMail always HTTP 400."""

    def list_inbox_messages(self) -> list[dict[str, Any]]:
        return []

    def get_message_mime(self, message_id: str) -> bytes:
        raise AssertionError("SEND1.2 must not get_message_mime")

    def list_new_chat_messages(self) -> list[dict[str, Any]]:
        return []

    def send_mime(self, rfc822: bytes) -> None:
        request = httpx.Request("POST", "https://graph.microsoft.com/v1.0/me/sendMail")
        response = httpx.Response(400, request=request)
        raise httpx.HTTPStatusError("Bad Request", request=request, response=response)

    def post_chat_message(self, chat_id: str, text: str) -> None:
        raise AssertionError("SEND1.2 must not post_chat_message")


@pytest.mark.integration
@pytest.mark.log_story
def test_scan_outbound_graph_400_retries_then_failed(
    sandbox: MailboxSandbox,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """After retry limit file is in spool/failed.

    :return: None
    """
    caplog.set_level(logging.INFO)
    conn = open_sandbox_db(sandbox)
    rfc822 = load_mail("hello-ada")
    spool = SpoolStore(sandbox.spool)
    enqueued = spool.enqueue(rfc822)
    scanner = OutboundScanner(conn, spool, _FailingSendGraph())

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
        beats={"error": ["reason=send_failed"]},
        level="ERROR",
    )
    conn.close()
