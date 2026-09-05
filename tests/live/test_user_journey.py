"""Live operator journey — real Graph user, real popd/smtpd, captured login.

Excluded from ``make test`` (``not live_graph``). Run ``make test-e2e`` with ``-s``
so the first device-code prompt is visible.
"""

from __future__ import annotations

import logging
import poplib
import smtplib
import ssl
from email.message import EmailMessage
from uuid import uuid4

import httpx
import pytest

from o365pop.accounts.store import get_account, get_encrypted_refresh_token
from o365pop.graph.http_adapter import GRAPH_ROOT
from o365pop.mailstore.maildir import MaildirStore
from o365pop.mailstore.spool import SpoolStore
from o365pop.smtpd.service import _make_controller
from o365pop.tosser.chat_address import encode_chat_id, reply_address
from o365pop.tosser.inbound import InboundTosser
from o365pop.tosser.index import upsert_chat_map
from o365pop.tosser.outbound_scanner import OutboundScanner
from tests.support.live_daemons import LIVE_POP_PORT, POP_HOST, start_live_popd, stop_live_popd
from tests.support.live_session import (
    LiveSession,
    build_probe_rfc822,
    ensure_captured_session,
    first_chat_id,
    live_bearer,
    live_graph,
    open_live_db,
    wait_inbox_subject,
)
from tests.support.log_story import assert_log_story

SMTP_HOST = "127.0.0.1"
LIVE_SMTP_PORT = 12587


@pytest.mark.live_graph
def test_act1_login_captured_for_real_user(
    live_session: LiveSession,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Device-code (or reused vault) leaves encrypted tokens; no raw bearer in sqlite.

    :return: None
    """
    caplog.set_level(logging.INFO)
    again = ensure_captured_session()
    assert again.username == live_session.username
    conn = open_live_db(live_session)
    try:
        account = get_account(conn)
        assert account is not None
        assert account.display_name == live_session.username
        refresh = get_encrypted_refresh_token(conn, live_session.settings.token_encryption_key)
        assert refresh
        raw = live_session.settings.db_path.read_bytes()
        assert b"eyJ" not in raw
        assert live_session.mailbox_password.encode() not in raw
    finally:
        conn.close()
    assert_log_story(
        caplog,
        where="live_session.ensure_captured_session",
        beats={"exit": [f"user={live_session.username}"]},
    )


@pytest.mark.live_graph
def test_act2_sync_probe_then_pop_collect(live_session: LiveSession) -> None:
    """sendMail probe → tosser → real POP RETR as the local mailbox user.

    :return: None
    """
    subject = f"o365pop-live-in-{uuid4().hex[:12]}"
    conn = open_live_db(live_session)
    proc = None
    try:
        graph = live_graph(live_session, conn)
        rfc822 = build_probe_rfc822(
            subject=subject,
            from_addr=live_session.username,
            to_addr=live_session.username,
            body="live act2 inbound probe",
        )
        graph.send_mime(rfc822)
        row = wait_inbox_subject(graph, subject)
        tossed = InboundTosser(conn, MaildirStore(live_session.settings.data_dir / "maildir"), graph).toss_outlook(row)
        assert tossed is True
        proc = start_live_popd(live_session, LIVE_POP_PORT)
        client = poplib.POP3(POP_HOST, LIVE_POP_PORT, timeout=8)
        assert not isinstance(client.sock, ssl.SSLSocket)
        assert client.user(live_session.mailbox_user).startswith(b"+OK")
        assert client.pass_(live_session.mailbox_password).startswith(b"+OK")
        count, _octets = client.stat()
        assert count >= 1
        found = False
        for index in range(1, count + 1):
            blob = b"\n".join(client.retr(index)[1])
            if subject.encode("utf-8") in blob:
                found = True
                break
        client.quit()
        assert found, f"POP RETR missed probe subject={subject}"
    finally:
        if proc is not None:
            stop_live_popd(proc)
        conn.close()


@pytest.mark.live_graph
def test_act3_smtp_sendmail_to_self(live_session: LiveSession) -> None:
    """AUTH LOGIN + DATA → scanner sendMail → spool/sent.

    :return: None
    """
    subject = f"o365pop-live-out-{uuid4().hex[:12]}"
    conn = open_live_db(live_session)
    controller = _make_controller(
        bind=SMTP_HOST,
        port=LIVE_SMTP_PORT,
        spool_root=live_session.settings.data_dir / "spool",
        db_path=live_session.settings.db_path,
    )
    controller.start()
    try:
        _smtp_send(
            live_session,
            subject=subject,
            to_addr=live_session.username,
            body="live act3 outbound probe",
        )
        graph = live_graph(live_session, conn)
        spool = SpoolStore(live_session.settings.data_dir / "spool")
        counts = OutboundScanner(conn, spool, graph).scan_once()
        assert counts["sent"] >= 1
        sent = list((live_session.settings.data_dir / "spool" / "sent").glob("*.eml"))
        assert any(subject.encode("utf-8") in path.read_bytes() for path in sent)
        wait_inbox_subject(graph, subject)
    finally:
        controller.stop()
        conn.close()


@pytest.mark.live_graph
def test_act4_teams_reply_posts_chat(live_session: LiveSession) -> None:
    """SMTP To teams.* → post_chat_message; no sendMail to that address.

    :return: None
    """
    conn = open_live_db(live_session)
    controller = _make_controller(
        bind=SMTP_HOST,
        port=LIVE_SMTP_PORT,
        spool_root=live_session.settings.data_dir / "spool",
        db_path=live_session.settings.db_path,
    )
    controller.start()
    try:
        graph = live_graph(live_session, conn)
        chat_id = first_chat_id(graph)
        if not chat_id:
            pytest.skip("no Teams chat; set LIVE_TEAMS_CHAT_ID or open a chat as this user")
        address = reply_address(chat_id)
        upsert_chat_map(conn, chat_id, address, encode_chat_id(chat_id))
        marker = f"o365pop-live-teams-{uuid4().hex[:12]}"
        _smtp_send(live_session, subject="Teams reply", to_addr=address, body=marker)
        spool = SpoolStore(live_session.settings.data_dir / "spool")
        counts = OutboundScanner(conn, spool, graph).scan_once()
        assert counts["sent"] >= 1
        assert _chat_has_text(live_bearer(live_session, conn), chat_id, marker)
    finally:
        controller.stop()
        conn.close()


def _smtp_send(session: LiveSession, *, subject: str, to_addr: str, body: str) -> None:
    """AUTH LOGIN and DATA on the live smtpd.

    :param session: Captured session. Example: result of ``ensure_captured_session()``
    :param subject: Subject. Example: ``"o365pop-live-out-abcd"``
    :param to_addr: Recipient. Example: ``"denis@contoso.com"``
    :param body: Plain body. Example: ``"probe"``
    :return: None
    """
    client = smtplib.SMTP(SMTP_HOST, LIVE_SMTP_PORT, timeout=8)
    try:
        assert not isinstance(getattr(client, "sock", None), ssl.SSLSocket)
        client.ehlo()
        assert "starttls" not in client.esmtp_features
        client.login(session.mailbox_user, session.mailbox_password)
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = session.username
        message["To"] = to_addr
        message.set_content(body)
        refused = client.send_message(message)
        assert refused == {}
        client.quit()
    except Exception:
        try:
            client.close()
        except OSError:
            pass
        raise


def _chat_has_text(access_token: str, chat_id: str, marker: str) -> bool:
    """Whether a recent chat message contains marker text.

    :param access_token: Bearer. Example: ``"eyJ0..."``
    :param chat_id: Graph chat id. Example: ``"19:general"``
    :param marker: Unique body. Example: ``"o365pop-live-teams-abcd"``
    :return: True if found. Example: ``True``
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    response = httpx.get(
        f"{GRAPH_ROOT}/chats/{chat_id}/messages?$top=15",
        headers=headers,
        timeout=30.0,
    )
    response.raise_for_status()
    payload = response.json()
    rows = list(payload.get("value") or [])
    for row in rows:
        body = row.get("body") if isinstance(row.get("body"), dict) else {}
        if marker in str(body.get("content") or ""):
            return True
    return False
