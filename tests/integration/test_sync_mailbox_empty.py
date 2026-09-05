"""SYNC1.3 — empty inbox/chats is completed tossed=0."""

from __future__ import annotations

import logging

import pytest

from o365pop.celery_app import celery_app
from o365pop.db import connect
from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.mailstore.maildir import MaildirStore
from o365pop.sync import tasks as sync_tasks
from tests.support.fixtures import load_graph_case
from tests.support.log_story import assert_log_story
from tests.support.mailbox import MailboxSandbox, open_sandbox_db


class _OkAuth:
    def ensure_bearer(self) -> str:
        return "test-bearer"


@pytest.mark.integration
@pytest.mark.log_story
def test_sync_mailbox_with_empty_graph_completes_zero_tossed(
    sandbox: MailboxSandbox, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """status=completed tossed=0.

    :return: None
    """
    caplog.set_level(logging.INFO)
    open_sandbox_db(sandbox).close()
    monkeypatch.setenv("DATA_DIR", str(sandbox.root))
    monkeypatch.setenv("DB_PATH", str(sandbox.db_path))
    monkeypatch.setenv("LOG_DIR", str(sandbox.log_dir))
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "1")
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    empty = FileGraphAdapter(load_graph_case("SYNC1.3-empty"))
    monkeypatch.setattr(sync_tasks, "auth_service_factory", lambda conn, settings: _OkAuth())
    monkeypatch.setattr(sync_tasks, "graph_factory", lambda settings, token: empty)

    result = sync_tasks.sync_mailbox.apply()
    assert result.successful()
    assert result.result == {"status": "completed", "error": None, "tossed": 0}

    conn = connect(sandbox.db_path)
    session = conn.execute("SELECT status, messages_tossed FROM sync_session").fetchone()
    assert session["status"] == "completed"
    assert session["messages_tossed"] == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM tossed_message").fetchone()["n"] == 0
    conn.close()

    assert MaildirStore(sandbox.maildir).list_uidls() == []
    assert_log_story(
        caplog,
        [
            {
                "where": "sync.tasks.sync_mailbox",
                "beat": "exit",
                "must_include": ["tossed=0"],
            }
        ],
    )
