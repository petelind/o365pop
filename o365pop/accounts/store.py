"""Single mailbox_account row (id=1) and encrypted token fields."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MailboxAccount:
    """Persisted mailbox row.

    :param display_name: Graph UPN or name. Example: ``"denis@example.com"``
    :param graph_user_id: Graph oid. Example: ``"00000000-0000-0000-0000-000000000001"``
    :param token_expires_at: Access-token expiry UTC. Example: ``datetime(2026, 9, 5, 18, 0)``
    :param mailbox_user: Local POP/SMTP user. Example: ``"denis"``
    """

    display_name: str | None
    graph_user_id: str | None
    token_expires_at: datetime | None
    mailbox_user: str | None


def get_account(conn: sqlite3.Connection) -> MailboxAccount | None:
    """Load the single mailbox row.

    :param conn: Open sqlite connection. Example: ``connect(path)``
    :return: Account or None. Example: ``MailboxAccount(display_name="denis@example.com", ...)``
    """
    logger.info("accounts.store.get_account | entry")
    raise NotImplementedError()


def upsert_account(
    conn: sqlite3.Connection,
    *,
    display_name: str,
    graph_user_id: str,
    mailbox_user: str,
    mailbox_password_hash: str,
) -> MailboxAccount:
    """Insert or replace mailbox_account id=1 (no tokens).

    :param conn: Open sqlite connection. Example: ``connect(path)``
    :param display_name: UPN. Example: ``"denis@example.com"``
    :param graph_user_id: Graph oid. Example: ``"00000000-0000-0000-0000-000000000001"``
    :param mailbox_user: Local USER. Example: ``"denis"``
    :param mailbox_password_hash: Local password hash. Example: ``"pbkdf2$..."``
    :return: Stored account. Example: ``MailboxAccount(...)``
    """
    logger.info("accounts.store.upsert_account | entry | user=%s", display_name)
    raise NotImplementedError()


def set_encrypted_access_token(conn: sqlite3.Connection, token: str, key: str) -> None:
    """Encrypt and store the access token. Empty token clears the field.

    :param conn: Open sqlite connection. Example: ``connect(path)``
    :param token: Plain access token or ``""``. Example: ``"eyJ0..."``
    :param key: Fernet key. Example: ``"gAAAAAB..."``
    :return: None
    """
    logger.info("accounts.store.set_encrypted_access_token | entry | clearing=%s", token == "")
    # 1. encrypt_token or NULL
    # 2. UPDATE mailbox_account SET encrypted_access_token
    raise NotImplementedError()


def get_encrypted_access_token(conn: sqlite3.Connection, key: str) -> str | None:
    """Decrypt the stored access token.

    :param conn: Open sqlite connection. Example: ``connect(path)``
    :param key: Fernet key. Example: ``"gAAAAAB..."``
    :return: Plain token or None. Example: ``"eyJ0..."``
    """
    logger.info("accounts.store.get_encrypted_access_token | entry")
    raise NotImplementedError()


def set_encrypted_refresh_token(conn: sqlite3.Connection, token: str, key: str) -> None:
    """Encrypt and store the refresh token. Empty token clears the field.

    :param conn: Open sqlite connection. Example: ``connect(path)``
    :param token: Plain refresh token or ``""``. Example: ``"M.R3..."``
    :param key: Fernet key. Example: ``"gAAAAAB..."``
    :return: None
    """
    logger.info("accounts.store.set_encrypted_refresh_token | entry | clearing=%s", token == "")
    raise NotImplementedError()


def get_encrypted_refresh_token(conn: sqlite3.Connection, key: str) -> str | None:
    """Decrypt the stored refresh token.

    :param conn: Open sqlite connection. Example: ``connect(path)``
    :param key: Fernet key. Example: ``"gAAAAAB..."``
    :return: Plain token or None. Example: ``"M.R3..."``
    """
    logger.info("accounts.store.get_encrypted_refresh_token | entry")
    raise NotImplementedError()


def set_token_expires_at(conn: sqlite3.Connection, expires_at: datetime | None) -> None:
    """Persist access-token expiry.

    :param conn: Open sqlite connection. Example: ``connect(path)``
    :param expires_at: UTC expiry or None. Example: ``datetime(2026, 9, 5, 18, 0)``
    :return: None
    """
    logger.info("accounts.store.set_token_expires_at | entry | expires_at=%s", expires_at)
    raise NotImplementedError()


def verify_local_password(conn: sqlite3.Connection, username: str, password: str) -> bool:
    """Check POP/SMTP credentials against the local hash.

    :param conn: Open sqlite connection. Example: ``connect(path)``
    :param username: Presented user. Example: ``"denis"``
    :param password: Presented password. Example: ``"local-pass"``
    :return: True if they match. Example: ``True``
    """
    logger.info("accounts.store.verify_local_password | entry | username=%s", username)
    raise NotImplementedError()
