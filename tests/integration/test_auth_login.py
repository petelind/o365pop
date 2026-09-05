"""AUTH1.1 — device-code login via DeviceCodePort fixture (no live Microsoft)."""

from __future__ import annotations

import logging

import pytest
from cryptography.fernet import Fernet

from o365pop.accounts.graph_auth import GraphAuthService
from o365pop.accounts.ports import TokenBundle
from o365pop.accounts.store import get_account, get_encrypted_access_token, get_encrypted_refresh_token
from o365pop.db import connect, init_schema
from tests.support.log_story import assert_log_story

ACCESS = "eyJ0-access-AUTH11-secret"
REFRESH = "M.R3-refresh-AUTH11-secret"


class FixtureDeviceCode:
    """DeviceCodePort that returns denis@example.com without Microsoft."""

    def login(self) -> TokenBundle:
        return TokenBundle(
            access_token=ACCESS,
            refresh_token=REFRESH,
            expires_in=3600,
            username="denis@example.com",
            oid="00000000-0000-0000-0000-000000000001",
        )


class FixtureMsal:
    """Unused on the login path."""

    def refresh(self, refresh_token: str) -> TokenBundle:
        raise AssertionError("login must not refresh")


@pytest.mark.integration
@pytest.mark.log_story
def test_login_device_code_with_fixture_stores_encrypted_tokens(tmp_db_path, caplog: pytest.LogCaptureFixture) -> None:
    """Persists encrypted tokens for denis@example.com and logs exit without secrets.

    :param caplog: pytest log capture. Example: test ``caplog``
    :return: None
    """
    caplog.set_level(logging.INFO)
    conn = connect(tmp_db_path)
    init_schema(conn)
    key = Fernet.generate_key().decode("ascii")
    service = GraphAuthService(conn, key, FixtureDeviceCode(), FixtureMsal())
    username = service.login_device_code()
    assert username == "denis@example.com"
    account = get_account(conn)
    assert account is not None
    assert account.display_name == "denis@example.com"
    assert account.token_expires_at is not None
    assert account.token_expires_at.tzinfo is not None
    assert get_encrypted_access_token(conn, key) == ACCESS
    assert get_encrypted_refresh_token(conn, key) == REFRESH
    raw = conn.execute(
        "SELECT encrypted_access_token, encrypted_refresh_token FROM mailbox_account WHERE id = 1"
    ).fetchone()
    assert ACCESS.encode() not in raw[0]
    assert REFRESH.encode() not in raw[1]
    assert_log_story(
        caplog,
        where="GraphAuthService.login_device_code",
        beats={"exit": ["user=denis@example.com"]},
    )
    joined = " ".join(record.getMessage() for record in caplog.records)
    assert ACCESS not in joined
    assert REFRESH not in joined
    conn.close()
