"""PALM1 — Palm-safe rewrite, publish, and local USER alias."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import pytest

from o365pop.accounts.store import _hash_local_password, upsert_account, verify_local_password
from o365pop.db import connect, init_schema
from o365pop.mailstore.maildir import MaildirStore
from o365pop.tosser.palm_view import (
    PALM_MAX_BYTES,
    PALM_UIDL_MAX,
    hash_palm_uidl,
    publish_palm_view,
    rewrite_palm_rfc822,
    save_hidden_uidls,
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


def _blank_plain_html(*, subject: str, html: str, when: datetime) -> bytes:
    """Outlook-style MIME: stub text/plain + real HTML.

    :param subject: Subject. Example: ``"Teams: ship"``
    :param html: HTML body. Example: ``"<p>Ship it</p>"``
    :param when: Date. Example: ``NOW``
    :return: RFC822 bytes. Example: ``b"Content-Type: multipart/..."``
    """
    date = format_datetime(when)
    return (
        f"From: Ada <ada@example.com>\r\nTo: denis@example.com\r\n"
        f"Subject: {subject}\r\nDate: {date}\r\nMIME-Version: 1.0\r\n"
        f"Content-Type: multipart/alternative; boundary=bound\r\n\r\n"
        f"--bound\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n \r\n"
        f"--bound\r\nContent-Type: text/html; charset=utf-8\r\n\r\n{html}\r\n"
        f"--bound--\r\n"
    ).encode("utf-8")


def _body_of(raw: bytes) -> bytes:
    """Bytes after the header blank line.

    :param raw: RFC822. Example: ``b"Subject: x\\r\\n\\r\\nHi\\r\\n"``
    :return: Body. Example: ``b"Hi\\r\\n"``
    """
    for sep in (b"\r\n\r\n", b"\n\n"):
        if sep in raw:
            return raw.split(sep, 1)[1]
    return b""


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
    assert b"MIME-Version:" not in rewritten
    assert b"Content-Transfer-Encoding: 7bit" in rewritten
    assert b"Content-Type: text/plain" in rewritten
    assert b"Date:" in rewritten
    assert b"visible words" in _body_of(rewritten)
    assert_log_story(caplog, where="tosser.palm_view.rewrite_palm_rfc822", beats={"exit": ["size=", "body_len="]})


@pytest.mark.unit
def test_rewrite_palm_rfc822_uses_html_when_text_plain_is_blank() -> None:
    """PALM1.6 stub text/plain must not hide the HTML body.

    :return: None
    """
    raw = _blank_plain_html(subject="Teams: ship", html="<p>Ship it from Teams</p>", when=NOW)
    rewritten = rewrite_palm_rfc822(raw, now=NOW)
    assert rewritten is not None
    body = _body_of(rewritten)
    assert b"Ship it from Teams" in body
    assert body.strip() != b""
    assert b"MIME-Version:" not in rewritten


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
        where="tosser.palm_view.rewrite_palm_rfc822",
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
    assert _body_of(rewritten).strip() != b""


@pytest.mark.unit
def test_rewrite_palm_rfc822_flattens_folded_optional_headers() -> None:
    """Folded Reply-To must not raise on rewrite.

    :return: None
    """
    raw = (
        f"From: Ada <ada@example.com>\r\nTo: denis@example.com\r\n"
        f"Subject: fold\r\nDate: {format_datetime(NOW)}\r\n"
        f"Reply-To: teams.longchatid@o365pop.local\r\n"
        f"\t (folded)\r\n\r\nHi\r\n"
    ).encode("utf-8")
    rewritten = rewrite_palm_rfc822(raw, now=NOW)
    assert rewritten is not None
    assert b"Reply-To:" in rewritten
    assert b"Hi" in _body_of(rewritten)


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
    assert b"Ship it" in _body_of(fresh)


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
def test_publish_palm_view_writes_hashed_7bit_and_skips_old(
    sandbox: MailboxSandbox, caplog: pytest.LogCaptureFixture
) -> None:
    """Fresh mail is hashed; old mail is dropped.

    :return: None
    """
    caplog.set_level("INFO")
    source = MaildirStore(sandbox.maildir)
    dest = MaildirStore(sandbox.root / "maildir-palm")
    source.add(_rfc822(subject="fresh", body="now", when=NOW), _LONG_UIDL)
    source.add(_rfc822(subject="old", body="then", when=NOW - timedelta(days=2)), "uid-outlook-old")
    counts = publish_palm_view(source, dest, now=NOW)
    assert counts["written"] == 1
    assert counts["dropped"] >= 1
    uidls = dest.iter_uidls()
    assert uidls == [hash_palm_uidl(_LONG_UIDL)]
    rfc = dest.get(uidls[0])
    assert b"multipart" not in rfc.lower()
    assert b"MIME-Version:" not in rfc
    assert b"now" in _body_of(rfc)
    assert_log_story(
        caplog,
        where="tosser.palm_view.publish",
        beats={"exit": ["written=1", "reused=0"]},
    )


@pytest.mark.unit
def test_publish_palm_view_skips_hidden_and_reuses_unchanged(sandbox: MailboxSandbox) -> None:
    """Hidden hashes stay out; a second publish reuses the dest file.

    :return: None
    """
    source = MaildirStore(sandbox.maildir)
    dest_root = sandbox.root / "maildir-palm"
    dest = MaildirStore(dest_root)
    source.add(_rfc822(subject="keep", body="visible", when=NOW), "uid-outlook-keep")
    source.add(_rfc822(subject="hide", body="gone", when=NOW), "uid-outlook-hide")
    hidden = hash_palm_uidl("uid-outlook-hide")
    save_hidden_uidls(dest_root, {hidden})
    first = publish_palm_view(source, dest, now=NOW)
    assert first["written"] == 1
    assert hidden not in dest.iter_uidls()
    second = publish_palm_view(MaildirStore(sandbox.maildir), MaildirStore(dest_root), now=NOW)
    assert second["written"] == 0
    assert second["reused"] == 1


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
