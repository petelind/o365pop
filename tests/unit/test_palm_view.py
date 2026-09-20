"""PALM1 — Palm-safe rewrite and local USER alias."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import pytest

from o365pop.accounts.store import _hash_local_password, upsert_account, verify_local_password
from o365pop.db import connect, init_schema
from o365pop.mailstore.maildir import MaildirStore
from o365pop.popd.palm import (
    PALM_MAX_BYTES,
    PALM_UIDL_MAX,
    hash_palm_uidl,
    list_palm_messages,
    rewrite_palm_rfc822,
)
from tests.support.log_story import assert_log_story
from tests.support.mailbox import MailboxSandbox

NOW = datetime(2026, 9, 20, 20, 0, tzinfo=UTC)
_LONG_UIDL = "uid-outlook-" + ("A" * 90)


def _rfc822(*, subject: str, body: str, when: datetime, html: bool = False) -> bytes:
    """Build a source message.

    :param subject: Subject. Example: ``"Q3 close"``
    :param body: Body text or HTML. Example: ``"<p>Hi</p>"``
    :param when: Date header. Example: ``NOW``
    :param html: Emit multipart/alternative when True. Example: ``True``
    :return: RFC822 bytes. Example: ``b"Subject: Q3 close\\r\\n"``
    """
    date = format_datetime(when)
    if not html:
        return (
            f"From: Ada <ada@example.com>\r\nTo: denis@example.com\r\n"
            f"Subject: {subject}\r\nDate: {date}\r\n"
            f"Content-Type: text/plain; charset=utf-8\r\n\r\n{body}\r\n"
        ).encode("utf-8")
    return (
        f"From: Ada <ada@example.com>\r\nTo: denis@example.com\r\n"
        f"Subject: {subject}\r\nDate: {date}\r\nMIME-Version: 1.0\r\n"
        f"Content-Type: multipart/alternative; boundary=bound\r\n\r\n"
        f"--bound\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nvisible words\r\n"
        f"--bound\r\nContent-Type: text/html; charset=utf-8\r\n\r\n{body}\r\n"
        f"--bound--\r\n"
    ).encode("utf-8")


@pytest.mark.unit
def test_rewrite_palm_rfc822_strips_multipart_and_sets_7bit_date(caplog: pytest.LogCaptureFixture) -> None:
    """HTML multipart becomes 7-bit text/plain with Date and CRLF.

    :return: None
    """
    caplog.set_level("INFO")
    raw = _rfc822(subject="Teams: ship", body="<p>Ship it</p>", when=NOW, html=True)
    rewritten = rewrite_palm_rfc822(raw, now=NOW)
    assert rewritten is not None
    assert len(rewritten) <= PALM_MAX_BYTES
    assert b"\r\n" in rewritten
    assert b"multipart" not in rewritten.lower()
    assert b"text/html" not in rewritten.lower()
    assert b"Content-Transfer-Encoding: 7bit" in rewritten
    assert b"Content-Type: text/plain" in rewritten
    assert b"Date:" in rewritten
    assert b"visible words" in rewritten
    assert_log_story(caplog, where="popd.palm.rewrite_palm_rfc822", beats={"exit": ["size="]})


@pytest.mark.unit
def test_rewrite_palm_rfc822_drops_mail_older_than_24h(caplog: pytest.LogCaptureFixture) -> None:
    """Date 48h ago is omitted from the Palm view.

    :return: None
    """
    caplog.set_level("INFO")
    old = NOW - timedelta(hours=48)
    raw = _rfc822(subject="old", body="stale", when=old)
    assert rewrite_palm_rfc822(raw, now=NOW) is None
    assert_log_story(
        caplog,
        where="popd.palm.rewrite_palm_rfc822",
        beats={"branch": ["skipped=true", "reason=too_old"]},
    )


@pytest.mark.unit
def test_rewrite_palm_rfc822_caps_size_at_5kb() -> None:
    """A huge body is truncated to ≤5120 bytes after rewrite.

    :return: None
    """
    raw = _rfc822(subject="huge", body="x" * 20_000, when=NOW)
    rewritten = rewrite_palm_rfc822(raw, now=NOW)
    assert rewritten is not None
    assert len(rewritten) <= PALM_MAX_BYTES


@pytest.mark.unit
def test_rewrite_palm_rfc822_uses_fallback_when_date_missing() -> None:
    """Teams-style mail without Date uses maildir mtime.

    :return: None
    """
    raw = b"From: Ada <ada@example.com>\r\nSubject: Teams\r\n\r\nShip it\r\n"
    old = NOW - timedelta(hours=48)
    assert rewrite_palm_rfc822(raw, now=NOW, fallback_when=old) is None
    fresh = rewrite_palm_rfc822(raw, now=NOW, fallback_when=NOW)
    assert fresh is not None
    assert b"Date:" in fresh


@pytest.mark.unit
def test_hash_palm_uidl_is_short_and_not_the_graph_id() -> None:
    """UIDL is a 64-char hash, never the Graph-style store id.

    :return: None
    """
    uidl = hash_palm_uidl(_LONG_UIDL)
    assert len(uidl) <= PALM_UIDL_MAX
    assert uidl.isascii()
    assert "AAMk" not in uidl
    assert _LONG_UIDL not in uidl
    assert hash_palm_uidl(_LONG_UIDL) == uidl


@pytest.mark.unit
def test_list_palm_messages_keeps_only_fresh_rewrites(sandbox: MailboxSandbox) -> None:
    """Old mail is dropped; fresh mail is hashed.

    :return: None
    """
    store = MaildirStore(sandbox.maildir)
    store.add(_rfc822(subject="fresh", body="now", when=NOW), _LONG_UIDL)
    store.add(_rfc822(subject="old", body="then", when=NOW - timedelta(days=2)), "uid-outlook-old")
    rows = list_palm_messages(store, now=NOW)
    assert len(rows) == 1
    store_uidl, palm_uidl, rfc = rows[0]
    assert store_uidl == _LONG_UIDL
    assert palm_uidl == hash_palm_uidl(_LONG_UIDL)
    assert b"multipart" not in rfc.lower()


@pytest.mark.unit
def test_verify_local_password_accepts_palm_alias(tmp_db_path) -> None:
    """USER palm shares the local mailbox password.

    :return: None
    """
    conn = connect(tmp_db_path)
    init_schema(conn)
    upsert_account(
        conn,
        display_name="denis@example.com",
        graph_user_id="00000000-0000-0000-0000-000000000001",
        mailbox_user="denis",
        mailbox_password_hash=_hash_local_password("local-pass"),
    )
    assert verify_local_password(conn, "denis", "local-pass") is True
    assert verify_local_password(conn, "palm", "local-pass") is True
    assert verify_local_password(conn, "palm", "wrong") is False
    assert verify_local_password(conn, "other", "local-pass") is False
    conn.close()
