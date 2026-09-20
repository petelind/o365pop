"""PALM1 — real poplib against the second POP view."""

from __future__ import annotations

import poplib
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import pytest

from o365pop.mailstore.maildir import MaildirStore
from o365pop.popd.palm import PALM_MAX_BYTES, PALM_UIDL_MAX, hash_palm_uidl
from tests.integration.test_pop_auth import _caplog_from_app_log
from tests.integration.test_pop_retrieve import POP_HOST, seed_local_account, start_popd, stop_popd
from tests.support.log_story import assert_log_story
from tests.support.mailbox import MailboxSandbox

POP_PALM_PORT = 11112
_LONG_UIDL = "uid-outlook-" + ("A" * 90)


def _fresh_html() -> bytes:
    """Multipart HTML with Date=now.

    :return: RFC822 bytes. Example: ``b"Content-Type: multipart/..."``
    """
    date = format_datetime(datetime.now(UTC))
    return (
        f"From: Ada <ada@example.com>\r\nTo: denis@example.com\r\n"
        f"Subject: Teams: ship\r\nDate: {date}\r\nMIME-Version: 1.0\r\n"
        f"Content-Type: multipart/alternative; boundary=bound\r\n\r\n"
        f"--bound\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nvisible words\r\n"
        f"--bound\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<p>Ship it</p>\r\n"
        f"--bound--\r\n"
    ).encode("utf-8")


def _dated(subject: str, body: str, when: datetime) -> bytes:
    """Plain message at an explicit Date.

    :param subject: Subject. Example: ``"old"``
    :param body: Body. Example: ``"stale"``
    :param when: Date. Example: ``datetime.now(UTC)``
    :return: RFC822 bytes. Example: ``b"Subject: old\\r\\n"``
    """
    return (
        f"From: Ada <ada@example.com>\r\nTo: denis@example.com\r\n"
        f"Subject: {subject}\r\nDate: {format_datetime(when)}\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n\r\n{body}\r\n"
    ).encode("utf-8")


def _uidls(client: poplib.POP3) -> list[bytes]:
    """UIDL tokens from a STAT listing.

    :param client: Authenticated POP3. Example: ``poplib.POP3(...)``
    :return: UIDL values. Example: ``[b"2c26b46b..."]``
    """
    return [line.split()[1] for line in client.uidl()[1]]


@pytest.mark.integration
@pytest.mark.log_story
def test_palm_user_retrieves_hashed_7bit_text(sandbox: MailboxSandbox) -> None:
    """PALM1.1 USER palm sees hash UIDL and text/plain 7-bit.

    :return: None
    """
    seed_local_account(sandbox)
    MaildirStore(sandbox.maildir).add(_fresh_html(), _LONG_UIDL)
    proc = start_popd(sandbox, POP_PALM_PORT)
    try:
        client = poplib.POP3(POP_HOST, POP_PALM_PORT, timeout=5)
        assert client.user("palm").startswith(b"+OK")
        assert client.pass_("local-pass").startswith(b"+OK")
        count, _octets = client.stat()
        assert count == 1
        uidl = _uidls(client)[0]
        assert len(uidl) <= PALM_UIDL_MAX
        assert uidl == hash_palm_uidl(_LONG_UIDL).encode("ascii")
        assert _LONG_UIDL.encode() not in uidl
        retr = b"\r\n".join(client.retr(1)[1])
        assert b"multipart" not in retr.lower()
        assert b"text/html" not in retr.lower()
        assert b"Content-Transfer-Encoding: 7bit" in retr
        assert b"Date:" in retr
        assert b"visible words" in retr
        assert len(retr) <= PALM_MAX_BYTES
        client.quit()
    finally:
        stop_popd(proc)
    assert_log_story(
        _caplog_from_app_log(sandbox.log_dir / "app.log"),
        [
            {
                "where": "popd.service._MailboxRealm.requestAvatar",
                "beat": "exit",
                "must_include": ["view=palm"],
            }
        ],
    )


@pytest.mark.integration
def test_palm_user_hides_mail_older_than_24h(sandbox: MailboxSandbox) -> None:
    """PALM1.2 only the fresh message is listed.

    :return: None
    """
    seed_local_account(sandbox)
    store = MaildirStore(sandbox.maildir)
    store.add(_dated("fresh", "now", datetime.now(UTC)), "uid-outlook-fresh")
    store.add(_dated("old", "then", datetime.now(UTC) - timedelta(hours=48)), "uid-outlook-old")
    proc = start_popd(sandbox, POP_PALM_PORT)
    try:
        client = poplib.POP3(POP_HOST, POP_PALM_PORT, timeout=5)
        client.user("palm")
        client.pass_("local-pass")
        count, _octets = client.stat()
        assert count == 1
        retr = b"\n".join(client.retr(1)[1])
        assert b"fresh" in retr
        assert b"old" not in retr or b"Subject: old" not in retr
        client.quit()
    finally:
        stop_popd(proc)


@pytest.mark.integration
def test_denis_still_sees_original_rfc822_on_same_popd(sandbox: MailboxSandbox) -> None:
    """PALM1.3 Entourage USER denis is unchanged.

    :return: None
    """
    seed_local_account(sandbox)
    MaildirStore(sandbox.maildir).add(_fresh_html(), _LONG_UIDL)
    proc = start_popd(sandbox, POP_PALM_PORT)
    try:
        client = poplib.POP3(POP_HOST, POP_PALM_PORT, timeout=5)
        client.user("denis")
        client.pass_("local-pass")
        uidls = _uidls(client)
        assert uidls == [_LONG_UIDL.encode()]
        retr = b"\n".join(client.retr(1)[1])
        assert b"multipart" in retr.lower()
        assert b"<p>Ship it</p>" in retr
        client.quit()
    finally:
        stop_popd(proc)


@pytest.mark.integration
def test_palm_dele_leaves_entourage_copy(sandbox: MailboxSandbox) -> None:
    """PALM1.4 Palm DELE hides only the Palm view.

    :return: None
    """
    seed_local_account(sandbox)
    store = MaildirStore(sandbox.maildir)
    store.add(_dated("keep-me", "body", datetime.now(UTC)), "uid-outlook-keep")
    proc = start_popd(sandbox, POP_PALM_PORT)
    try:
        palm = poplib.POP3(POP_HOST, POP_PALM_PORT, timeout=5)
        palm.user("palm")
        palm.pass_("local-pass")
        assert palm.stat()[0] >= 1
        palm.dele(1)
        palm.quit()
        denis = poplib.POP3(POP_HOST, POP_PALM_PORT, timeout=5)
        denis.user("denis")
        denis.pass_("local-pass")
        blob = b"\n".join(sum((denis.retr(i + 1)[1] for i in range(denis.stat()[0])), []))
        assert b"keep-me" in blob
        denis.quit()
    finally:
        stop_popd(proc)
