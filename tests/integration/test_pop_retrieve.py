"""POP1.1 — real poplib, no TLS."""

from __future__ import annotations

import poplib
import socket
import ssl
import time
from multiprocessing import Process
from pathlib import Path

import pytest

from o365pop.accounts.store import _hash_local_password, upsert_account
from o365pop.mailstore.maildir import MaildirStore
from tests.support.mailbox import MailboxSandbox, open_sandbox_db

POP_HOST = "127.0.0.1"
POP_PORT = 11110
_RFC822 = b"From: tester@example.com\r\nSubject: Q3 close\r\n\r\nBody line\r\n"


def _run_popd_process(bind: str, port: int, maildir: str, db_path: str, log_dir: str) -> None:
    """Child process: block on Twisted reactor.

    :param bind: Listen address. Example: ``"127.0.0.1"``
    :param port: Listen port. Example: ``11110``
    :param maildir: Maildir path. Example: ``"/tmp/maildir"``
    :param db_path: sqlite path. Example: ``"/tmp/o365pop.sqlite3"``
    :param log_dir: Child app.log directory. Example: ``"/tmp/logs"``
    :return: None
    """
    from o365pop.logging_setup import configure_logging
    from o365pop.popd.service import run_popd

    configure_logging(Path(log_dir))
    run_popd(bind=bind, port=port, maildir=Path(maildir), db_path=Path(db_path))


def wait_port(host: str, port: int, timeout: float = 5.0) -> None:
    """Block until TCP accept works.

    :param host: Address. Example: ``"127.0.0.1"``
    :param port: Port. Example: ``11110``
    :param timeout: Seconds. Example: ``5.0``
    :return: None
    :raises TimeoutError: if the port never opens
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError(f"{host}:{port} did not open")


def seed_local_account(sandbox: MailboxSandbox, *, password: str = "local-pass") -> None:
    """Account denis / local-pass (and USER palm alias).

    :param sandbox: Isolated paths. Example: ``mailbox_sandbox(...)``
    :param password: Local PASS. Example: ``"local-pass"``
    :return: None
    """
    conn = open_sandbox_db(sandbox)
    upsert_account(
        conn,
        display_name="denis@example.com",
        graph_user_id="00000000-0000-0000-0000-000000000001",
        mailbox_user="denis",
        mailbox_password_hash=_hash_local_password(password),
    )
    conn.close()


def seed_local_mailbox(sandbox: MailboxSandbox, *, password: str = "local-pass") -> None:
    """Account denis + one RFC822 UIDL uid-outlook-1.

    :param sandbox: Isolated paths. Example: ``mailbox_sandbox(...)``
    :param password: Local PASS. Example: ``"local-pass"``
    :return: None
    """
    seed_local_account(sandbox, password=password)
    MaildirStore(sandbox.maildir).add(_RFC822, "uid-outlook-1")


def start_popd(sandbox: MailboxSandbox, port: int) -> Process:
    """Spawn run_popd in a child process.

    :param sandbox: Isolated paths. Example: ``mailbox_sandbox(...)``
    :param port: Listen port. Example: ``11110``
    :return: Started process. Example: ``<Process>``
    """
    proc = Process(
        target=_run_popd_process,
        args=(POP_HOST, port, str(sandbox.maildir), str(sandbox.db_path), str(sandbox.log_dir)),
        daemon=True,
    )
    proc.start()
    wait_port(POP_HOST, port)
    return proc


def stop_popd(proc: Process) -> None:
    """Terminate the child popd.

    :param proc: Process from start_popd. Example: ``<Process>``
    :return: None
    """
    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=5)


@pytest.mark.integration
def test_pop_stat_uidl_retr_top_without_tls(sandbox: MailboxSandbox) -> None:
    """USER/PASS STAT=1 UIDL RETR Subject TOP headers.

    :return: None
    """
    seed_local_mailbox(sandbox)
    proc = start_popd(sandbox, POP_PORT)
    try:
        client = poplib.POP3(POP_HOST, POP_PORT, timeout=5)
        assert not isinstance(client.sock, ssl.SSLSocket)
        welcome = client.getwelcome()
        assert welcome.startswith(b"+OK")
        assert b"<" not in welcome
        assert b"@" not in welcome
        assert client.user("denis").startswith(b"+OK")
        assert client.pass_("local-pass").startswith(b"+OK")
        count, _octets = client.stat()
        assert count == 1
        uidl_listing = client.uidl()
        uidl_blob = b"\n".join(uidl_listing[1])
        assert b"uid-outlook-1" in uidl_blob
        retr_blob = b"\n".join(client.retr(1)[1])
        assert b"Subject: Q3 close" in retr_blob
        top_blob = b"\n".join(client.top(1, 0)[1])
        assert b"Subject: Q3 close" in top_blob
        assert b"Body line" not in top_blob
        client.quit()
    finally:
        stop_popd(proc)
