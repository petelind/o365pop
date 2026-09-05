"""AUTH1.2 — refresh expired access token."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet

from o365pop.accounts.errors import AuthenticationError
from o365pop.accounts.graph_auth import GraphAuthService
from o365pop.accounts.ports import TokenBundle
from o365pop.accounts.store import (
    get_account,
    get_encrypted_access_token,
    set_encrypted_access_token,
    set_encrypted_refresh_token,
    set_token_expires_at,
    upsert_account,
)
from o365pop.db import connect, init_schema


class _RejectMsal:
    def refresh(self, refresh_token: str) -> TokenBundle:
        raise AuthenticationError("refresh_token_rejected")


class _RenewMsal:
    def refresh(self, refresh_token: str) -> TokenBundle:
        assert refresh_token == "M.R3-stored-refresh"
        return TokenBundle(access_token="eyJ0-new-access", refresh_token="M.R3-new-refresh", expires_in=3600)


class _NoopDevice:
    def login(self) -> TokenBundle:
        raise AssertionError("refresh path must not login")


def _seed_expired(conn, key: str) -> None:
    upsert_account(
        conn,
        display_name="denis@example.com",
        graph_user_id="00000000-0000-0000-0000-000000000001",
        mailbox_user="denis",
        mailbox_password_hash="pbkdf2$unused",
    )
    set_encrypted_access_token(conn, "eyJ0-old-access", key)
    set_encrypted_refresh_token(conn, "M.R3-stored-refresh", key)
    set_token_expires_at(conn, datetime.now(UTC) - timedelta(minutes=5))


@pytest.mark.unit
def test_refresh_access_token_with_expired_access_stores_new_expiry(tmp_db_path) -> None:
    """Expired access + valid refresh stores a future expiry.

    :return: None
    """
    conn = connect(tmp_db_path)
    init_schema(conn)
    key = Fernet.generate_key().decode("ascii")
    _seed_expired(conn, key)
    service = GraphAuthService(conn, key, _NoopDevice(), _RenewMsal())
    token = service.ensure_bearer()
    assert token == "eyJ0-new-access"
    assert get_encrypted_access_token(conn, key) == "eyJ0-new-access"
    account = get_account(conn)
    assert account is not None
    assert account.token_expires_at is not None
    assert account.token_expires_at > datetime.now(UTC)
    conn.close()


@pytest.mark.unit
def test_refresh_access_token_with_revoked_refresh_raises_authentication_error(tmp_db_path) -> None:
    """Rejected refresh raises AuthenticationError.

    :return: None
    """
    conn = connect(tmp_db_path)
    init_schema(conn)
    key = Fernet.generate_key().decode("ascii")
    _seed_expired(conn, key)
    service = GraphAuthService(conn, key, _NoopDevice(), _RejectMsal())
    with pytest.raises(AuthenticationError):
        service.refresh_access_token()
    conn.close()
