"""SMTP1.1 — AUTH LOGIN + DATA → spool; Graph unused."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

import pytest

from o365pop.accounts.store import _hash_local_password, upsert_account
from o365pop.smtpd.service import _make_controller
from tests.support.mailbox import MailboxSandbox, open_sandbox_db

SMTP_HOST = "127.0.0.1"
SMTP_PORT = 10587


@pytest.mark.integration
def test_smtp_auth_login_data_writes_spool_without_graph(sandbox: MailboxSandbox) -> None:
    """Subject Hello Ada in spool/new.

    :return: None
    """
    conn = open_sandbox_db(sandbox)
    upsert_account(
        conn,
        display_name="denis@example.com",
        graph_user_id="00000000-0000-0000-0000-000000000001",
        mailbox_user="denis",
        mailbox_password_hash=_hash_local_password("local-pass"),
    )
    conn.close()

    controller = _make_controller(
        bind=SMTP_HOST,
        port=SMTP_PORT,
        spool_root=sandbox.spool,
        db_path=sandbox.db_path,
    )
    controller.start()
    try:
        client = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5)
        assert not isinstance(getattr(client, "sock", None), ssl.SSLSocket)
        client.ehlo()
        assert "starttls" not in client.esmtp_features
        client.login("denis", "local-pass")
        message = EmailMessage()
        message["Subject"] = "Hello Ada"
        message["From"] = "denis@example.com"
        message["To"] = "ada@example.com"
        message.set_content("Hi Ada")
        refused = client.send_message(message)
        assert refused == {}
        client.quit()
    finally:
        controller.stop()

    new_dir = sandbox.spool / "new"
    files = list(new_dir.glob("*.eml"))
    assert len(files) == 1
    assert b"Subject: Hello Ada" in files[0].read_bytes()
    assert "from o365pop.graph" not in Path("o365pop/smtpd/handler.py").read_text(encoding="utf-8")
    assert "from o365pop.graph" not in Path("o365pop/smtpd/service.py").read_text(encoding="utf-8")
