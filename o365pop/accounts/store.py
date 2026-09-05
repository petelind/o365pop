"""Single mailbox_account row (id=1) and encrypted token fields."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from o365pop.accounts.crypto import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

ACCOUNT_ID = 1
_PBKDF2_ROUNDS = 210_000


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
    row = conn.execute("SELECT * FROM mailbox_account WHERE id = ?", (ACCOUNT_ID,)).fetchone()
    if row is None:
        logger.info("accounts.store.get_account | exit | present=false")
        return None
    account = _row_to_account(row)
    logger.info("accounts.store.get_account | exit | user=%s", account.display_name)
    return account


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
    now = _now_iso()
    existing = conn.execute("SELECT id FROM mailbox_account WHERE id = ?", (ACCOUNT_ID,)).fetchone()
    if existing is None:
        conn.execute(
            """
            INSERT INTO mailbox_account (
                id, display_name, graph_user_id, mailbox_user, mailbox_password_hash,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ACCOUNT_ID, display_name, graph_user_id, mailbox_user, mailbox_password_hash, now, now),
        )
    else:
        conn.execute(
            """
            UPDATE mailbox_account
            SET display_name = ?, graph_user_id = ?, mailbox_user = ?,
                mailbox_password_hash = ?, updated_at = ?
            WHERE id = ?
            """,
            (display_name, graph_user_id, mailbox_user, mailbox_password_hash, now, ACCOUNT_ID),
        )
    conn.commit()
    account = get_account(conn)
    if account is None:
        raise RuntimeError("mailbox_account row missing after upsert")
    logger.info("accounts.store.upsert_account | exit | user=%s", account.display_name)
    return account


def set_encrypted_access_token(conn: sqlite3.Connection, token: str, key: str) -> None:
    """Encrypt and store the access token. Empty token clears the field.

    :param conn: Open sqlite connection. Example: ``connect(path)``
    :param token: Plain access token or ``""``. Example: ``"eyJ0..."``
    :param key: Fernet key. Example: ``"gAAAAAB..."``
    :return: None
    """
    logger.info("accounts.store.set_encrypted_access_token | entry | clearing=%s", token == "")
    _write_token_blob(conn, "encrypted_access_token", token, key)
    logger.info("accounts.store.set_encrypted_access_token | exit | clearing=%s", token == "")


def get_encrypted_access_token(conn: sqlite3.Connection, key: str) -> str | None:
    """Decrypt the stored access token.

    :param conn: Open sqlite connection. Example: ``connect(path)``
    :param key: Fernet key. Example: ``"gAAAAAB..."``
    :return: Plain token or None. Example: ``"eyJ0..."``
    """
    logger.info("accounts.store.get_encrypted_access_token | entry")
    token = _read_token_blob(conn, "encrypted_access_token", key)
    logger.info("accounts.store.get_encrypted_access_token | exit | present=%s", token is not None)
    return token


def set_encrypted_refresh_token(conn: sqlite3.Connection, token: str, key: str) -> None:
    """Encrypt and store the refresh token. Empty token clears the field.

    :param conn: Open sqlite connection. Example: ``connect(path)``
    :param token: Plain refresh token or ``""``. Example: ``"M.R3..."``
    :param key: Fernet key. Example: ``"gAAAAAB..."``
    :return: None
    """
    logger.info("accounts.store.set_encrypted_refresh_token | entry | clearing=%s", token == "")
    _write_token_blob(conn, "encrypted_refresh_token", token, key)
    logger.info("accounts.store.set_encrypted_refresh_token | exit | clearing=%s", token == "")


def get_encrypted_refresh_token(conn: sqlite3.Connection, key: str) -> str | None:
    """Decrypt the stored refresh token.

    :param conn: Open sqlite connection. Example: ``connect(path)``
    :param key: Fernet key. Example: ``"gAAAAAB..."``
    :return: Plain token or None. Example: ``"M.R3..."``
    """
    logger.info("accounts.store.get_encrypted_refresh_token | entry")
    token = _read_token_blob(conn, "encrypted_refresh_token", key)
    logger.info("accounts.store.get_encrypted_refresh_token | exit | present=%s", token is not None)
    return token


def set_token_expires_at(conn: sqlite3.Connection, expires_at: datetime | None) -> None:
    """Persist access-token expiry.

    :param conn: Open sqlite connection. Example: ``connect(path)``
    :param expires_at: UTC expiry or None. Example: ``datetime(2026, 9, 5, 18, 0)``
    :return: None
    """
    logger.info("accounts.store.set_token_expires_at | entry | expires_at=%s", expires_at)
    _ensure_account_row(conn)
    value = expires_at.astimezone(UTC).isoformat() if expires_at is not None else None
    conn.execute(
        "UPDATE mailbox_account SET token_expires_at = ?, updated_at = ? WHERE id = ?",
        (value, _now_iso(), ACCOUNT_ID),
    )
    conn.commit()
    logger.info("accounts.store.set_token_expires_at | exit | stored=%s", value is not None)


def verify_local_password(conn: sqlite3.Connection, username: str, password: str) -> bool:
    """Check POP/SMTP credentials against the local hash.

    :param conn: Open sqlite connection. Example: ``connect(path)``
    :param username: Presented user. Example: ``"denis"``
    :param password: Presented password. Example: ``"local-pass"``
    :return: True if they match. Example: ``True``
    """
    logger.info("accounts.store.verify_local_password | entry | username=%s", username)
    row = conn.execute(
        "SELECT mailbox_user, mailbox_password_hash FROM mailbox_account WHERE id = ?",
        (ACCOUNT_ID,),
    ).fetchone()
    if row is None or not row["mailbox_user"] or not row["mailbox_password_hash"]:
        logger.info("accounts.store.verify_local_password | exit | matched=false reason=missing")
        return False
    matched = hmac.compare_digest(row["mailbox_user"], username) and _verify_password(
        password, row["mailbox_password_hash"]
    )
    logger.info("accounts.store.verify_local_password | exit | matched=%s", matched)
    return matched


def _hash_local_password(password: str) -> str:
    """Hash a local mailbox password (never the Microsoft password).

    :param password: Local password. Example: ``"local-only"``
    :return: Encoded hash. Example: ``"pbkdf2$210000$ab12$cd34"``
    """
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2${_PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def _write_token_blob(conn: sqlite3.Connection, column: str, token: str, key: str) -> None:
    """Encrypt (or clear) one token column.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param column: Column name. Example: ``"encrypted_access_token"``
    :param token: Plain token or empty. Example: ``"eyJ0..."``
    :param key: Fernet key. Example: ``"gAAAAAB..."``
    :return: None
    """
    _ensure_account_row(conn)
    blob = encrypt_token(token, key) if token else None
    conn.execute(
        f"UPDATE mailbox_account SET {column} = ?, updated_at = ? WHERE id = ?",
        (blob, _now_iso(), ACCOUNT_ID),
    )
    conn.commit()


def _read_token_blob(conn: sqlite3.Connection, column: str, key: str) -> str | None:
    """Decrypt one token column.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param column: Column name. Example: ``"encrypted_access_token"``
    :param key: Fernet key. Example: ``"gAAAAAB..."``
    :return: Plain token or None. Example: ``"eyJ0..."``
    """
    row = conn.execute(f"SELECT {column} FROM mailbox_account WHERE id = ?", (ACCOUNT_ID,)).fetchone()
    if row is None or row[0] is None:
        return None
    return decrypt_token(row[0], key)


def _get_password_hash(conn: sqlite3.Connection) -> str:
    """Return the stored local password hash or empty.

    :param conn: sqlite connection. Example: ``connect(path)``
    :return: Hash or ``""``. Example: ``"pbkdf2$210000$ab$cd"``
    """
    row = conn.execute(
        "SELECT mailbox_password_hash FROM mailbox_account WHERE id = ?",
        (ACCOUNT_ID,),
    ).fetchone()
    if row is None or not row[0]:
        return ""
    return str(row[0])


def _ensure_account_row(conn: sqlite3.Connection) -> None:
    """Insert an empty id=1 row when token writes happen first.

    :param conn: sqlite connection. Example: ``connect(path)``
    :return: None
    """
    now = _now_iso()
    conn.execute(
        """
        INSERT OR IGNORE INTO mailbox_account (id, created_at, updated_at)
        VALUES (?, ?, ?)
        """,
        (ACCOUNT_ID, now, now),
    )


def _row_to_account(row: sqlite3.Row) -> MailboxAccount:
    """Map a sqlite row to MailboxAccount.

    :param row: mailbox_account row. Example: ``conn.execute(...).fetchone()``
    :return: Account dataclass. Example: ``MailboxAccount(...)``
    """
    raw_expiry = row["token_expires_at"]
    expiry = datetime.fromisoformat(raw_expiry) if raw_expiry else None
    return MailboxAccount(
        display_name=row["display_name"],
        graph_user_id=row["graph_user_id"],
        token_expires_at=expiry,
        mailbox_user=row["mailbox_user"],
    )


def _now_iso() -> str:
    """UTC timestamp for created_at/updated_at.

    :return: ISO string. Example: ``"2026-09-05T21:00:00+00:00"``
    """
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _verify_password(password: str, encoded: str) -> bool:
    """Compare a password to a pbkdf2$ encoded hash.

    :param password: Presented password. Example: ``"local-only"``
    :param encoded: Stored hash. Example: ``"pbkdf2$210000$ab$cd"``
    :return: True on match. Example: ``True``
    """
    parts = encoded.split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2":
        return False
    rounds = int(parts[1])
    salt = bytes.fromhex(parts[2])
    expected = bytes.fromhex(parts[3])
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return hmac.compare_digest(digest, expected)
