"""AUTH1.3 — revoked refresh fails sync_mailbox without retry."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet

from o365pop.accounts.errors import AuthenticationError
from o365pop.accounts.graph_auth import GraphAuthService
from o365pop.accounts.ports import TokenBundle
from o365pop.accounts.store import (
    set_encrypted_access_token,
    set_encrypted_refresh_token,
    set_token_expires_at,
    upsert_account,
)
from o365pop.celery_app import celery_app
from o365pop.db import connect, init_schema
from o365pop.sync import tasks as sync_tasks
from tests.support.log_story import assert_log_story


class _RevokedMsal:
    def refresh(self, refresh_token: str) -> TokenBundle:
        raise AuthenticationError("refresh_token_rejected")


class _NoopDevice:
    def login(self) -> TokenBundle:
        raise AssertionError("revoked path must not login")


@pytest.mark.integration
@pytest.mark.log_story
def test_sync_mailbox_with_revoked_refresh_marks_failed_and_does_not_retry(
    tmp_db_path, tmp_log_dir, monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Eager Celery: session failed, task not re-enqueued, log reason=auth_failed.

    :param caplog: pytest log capture. Example: test ``caplog``
    :return: None
    """
    caplog.set_level(logging.INFO)
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", key)
    monkeypatch.setenv("DB_PATH", str(tmp_db_path))
    monkeypatch.setenv("LOG_DIR", str(tmp_log_dir))
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "1")
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    conn = connect(tmp_db_path)
    init_schema(conn)
    upsert_account(
        conn,
        display_name="denis@example.com",
        graph_user_id="00000000-0000-0000-0000-000000000001",
        mailbox_user="denis",
        mailbox_password_hash="pbkdf2$unused",
    )
    set_encrypted_access_token(conn, "eyJ0-expired", key)
    set_encrypted_refresh_token(conn, "M.R3-revoked", key)
    set_token_expires_at(conn, datetime.now(UTC) - timedelta(hours=1))
    conn.close()

    def factory(factory_conn, settings):
        return GraphAuthService(factory_conn, settings.token_encryption_key, _NoopDevice(), _RevokedMsal())

    monkeypatch.setattr(sync_tasks, "auth_service_factory", factory)

    result = sync_tasks.sync_mailbox.apply()
    assert result.successful()
    assert result.result == {"status": "failed", "error": "auth_failed"}
    assert not result.retries

    conn = connect(tmp_db_path)
    rows = conn.execute("SELECT status, error FROM sync_session").fetchall()
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"
    assert rows[0]["error"] == "auth_failed"
    conn.close()

    assert_log_story(
        caplog,
        [
            {
                "where": "sync.tasks.sync_mailbox",
                "beat": "error",
                "must_include": ["reason=auth_failed"],
                "level": "ERROR",
            }
        ],
    )
    joined = " ".join(record.getMessage() for record in caplog.records)
    assert "M.R3-revoked" not in joined
    assert os.getenv("TOKEN_ENCRYPTION_KEY") == key
