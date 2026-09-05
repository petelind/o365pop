"""AUTH1.1 — Fernet vault; no plaintext tokens in sqlite."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from o365pop.accounts.crypto import decrypt_token, encrypt_token
from o365pop.accounts.store import (
    get_encrypted_access_token,
    set_encrypted_access_token,
    upsert_account,
)
from o365pop.db import connect, init_schema


@pytest.mark.unit
def test_encrypt_token_roundtrip_returns_original() -> None:
    """encrypt then decrypt yields the same token string.

    :return: None
    """
    key = Fernet.generate_key().decode("ascii")
    token = "eyJ0eXAiOi-AUTH11-access"
    blob = encrypt_token(token, key)
    assert decrypt_token(blob, key) == token
    assert token.encode() not in blob


@pytest.mark.unit
def test_set_encrypted_access_token_does_not_store_plaintext(tmp_db_path) -> None:
    """sqlite BLOB must not contain the raw token.

    :return: None
    """
    conn = connect(tmp_db_path)
    init_schema(conn)
    key = Fernet.generate_key().decode("ascii")
    token = "eyJ0eXAiOi-plaintext-must-not-land"
    upsert_account(
        conn,
        display_name="denis@example.com",
        graph_user_id="00000000-0000-0000-0000-000000000001",
        mailbox_user="denis",
        mailbox_password_hash="pbkdf2$unused",
    )
    set_encrypted_access_token(conn, token, key)
    raw = conn.execute("SELECT encrypted_access_token FROM mailbox_account WHERE id = 1").fetchone()
    assert raw is not None
    blob = raw[0]
    assert blob is not None
    assert token.encode() not in blob
    assert get_encrypted_access_token(conn, key) == token
    conn.close()


@pytest.mark.unit
def test_set_encrypted_access_token_with_empty_string_clears_field(tmp_db_path) -> None:
    """Empty token stores NULL / missing.

    :return: None
    """
    conn = connect(tmp_db_path)
    init_schema(conn)
    key = Fernet.generate_key().decode("ascii")
    upsert_account(
        conn,
        display_name="denis@example.com",
        graph_user_id="00000000-0000-0000-0000-000000000001",
        mailbox_user="denis",
        mailbox_password_hash="pbkdf2$unused",
    )
    set_encrypted_access_token(conn, "eyJ0-temp", key)
    set_encrypted_access_token(conn, "", key)
    raw = conn.execute("SELECT encrypted_access_token FROM mailbox_account WHERE id = 1").fetchone()
    assert raw is not None
    assert raw[0] is None
    assert get_encrypted_access_token(conn, key) is None
    conn.close()
