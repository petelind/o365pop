"""Isolated maildir / spool / sqlite sandbox for integration tests."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from sqlite3 import Connection

from o365pop.db import connect, init_schema
from tests.support.fixtures import load_preset

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MailboxSandbox:
    """Per-test filesystem and database roots.

    :param root: Temp workspace. Example: ``Path("/tmp/pytest-.../sandbox")``
    :param db_path: SQLite file. Example: ``Path(".../data/o365pop.sqlite3")``
    :param maildir: Inbound maildir. Example: ``Path(".../maildir")``
    :param spool: Outbound spool. Example: ``Path(".../spool")``
    :param log_dir: Log directory. Example: ``Path(".../logs")``
    """

    root: Path
    db_path: Path
    maildir: Path
    spool: Path
    log_dir: Path


def mailbox_sandbox(root: Path) -> MailboxSandbox:
    """Create empty maildir/spool/data directories under ``root``.

    :param root: Parent directory. Example: ``tmp_path / "sandbox"``
    :return: Sandbox paths. Example: ``MailboxSandbox(root=..., ...)``
    """
    logger.info("mailbox.mailbox_sandbox | entry | root=%s", root)
    data = root / "data"
    maildir = root / "maildir"
    spool = root / "spool"
    log_dir = root / "logs"
    for path in (data, log_dir):
        path.mkdir(parents=True, exist_ok=True)
    for folder in ("cur", "new", "tmp"):
        (maildir / folder).mkdir(parents=True, exist_ok=True)
    for folder in ("new", "retry", "sent", "failed"):
        (spool / folder).mkdir(parents=True, exist_ok=True)
    sandbox = MailboxSandbox(
        root=root,
        db_path=data / "o365pop.sqlite3",
        maildir=maildir,
        spool=spool,
        log_dir=log_dir,
    )
    logger.info("mailbox.mailbox_sandbox | exit | db_path=%s", sandbox.db_path)
    return sandbox


def open_sandbox_db(sandbox: MailboxSandbox) -> Connection:
    """Open sqlite and apply ``schema.sql``.

    :param sandbox: Isolated paths. Example: result of ``mailbox_sandbox(...)``
    :return: Connection. Example: ``<sqlite3.Connection>``
    """
    logger.info("mailbox.open_sandbox_db | entry | db_path=%s", sandbox.db_path)
    conn = connect(sandbox.db_path)
    init_schema(conn)
    logger.info("mailbox.open_sandbox_db | exit | status=ok")
    return conn


def apply_preset(conn: Connection, preset_id: str) -> None:
    """Insert preset rows (AUTH writes real tokens later).

    :param conn: Open sqlite connection. Example: result of ``open_sandbox_db``
    :param preset_id: Catalog preset. Example: ``"authenticated_mailbox"``
    :return: None
    """
    logger.info("mailbox.apply_preset | entry | preset_id=%s", preset_id)
    payload = load_preset(preset_id)
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    for row in payload.get("mailbox_account", []):
        conn.execute(
            """
            INSERT OR REPLACE INTO mailbox_account (
                id, display_name, graph_user_id,
                encrypted_access_token, encrypted_refresh_token, token_expires_at,
                mailbox_user, mailbox_password_hash, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row.get("display_name"),
                row.get("graph_user_id"),
                row.get("encrypted_access_token"),
                row.get("encrypted_refresh_token"),
                row.get("token_expires_at"),
                row.get("mailbox_user"),
                row.get("mailbox_password_hash"),
                now,
                now,
            ),
        )
    conn.commit()
    logger.info("mailbox.apply_preset | exit | mailbox_rows=%s", len(payload.get("mailbox_account", [])))
