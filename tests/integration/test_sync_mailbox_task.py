"""SYNC — eager Celery pull+toss of Outlook + Teams fixtures."""

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


class _InboxAndChatsGraph:
    """Compose two FileGraphAdapters (Outlook MIME + Teams lines)."""

    def __init__(self, inbox: FileGraphAdapter, chats: FileGraphAdapter) -> None:
        self._inbox = inbox
        self._chats = chats

    def list_inbox_messages(self) -> list:
        return self._inbox.list_inbox_messages()

    def get_message_mime(self, message_id: str) -> bytes:
        return self._inbox.get_message_mime(message_id)

    def list_new_chat_messages(self) -> list:
        return self._chats.list_new_chat_messages()

    def send_mime(self, rfc822: bytes) -> None:
        raise AssertionError("sync_mailbox must not send_mime")

    def post_chat_message(self, chat_id: str, text: str) -> None:
        raise AssertionError("sync_mailbox must not post_chat_message")


@pytest.mark.integration
@pytest.mark.log_story
def test_sync_mailbox_eager_tosses_file_graph_case(
    sandbox: MailboxSandbox, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Completed session with tossed>=1 on SYNC1.1 + SYNC1.2 fixtures.

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

    outlook = FileGraphAdapter(load_graph_case("SYNC1.1-outlook-q3-close"))
    teams = FileGraphAdapter(load_graph_case("SYNC1.2-teams-ship-it"))
    monkeypatch.setattr(sync_tasks, "auth_service_factory", lambda conn, settings: _OkAuth())
    monkeypatch.setattr(sync_tasks, "graph_factory", lambda settings, token: _InboxAndChatsGraph(outlook, teams))

    result = sync_tasks.sync_mailbox.apply()
    assert result.successful()
    assert result.result["status"] == "completed"
    assert result.result["tossed"] >= 1

    conn = connect(sandbox.db_path)
    session = conn.execute("SELECT status, messages_tossed FROM sync_session").fetchone()
    assert session["status"] == "completed"
    assert session["messages_tossed"] >= 1
    sources = {row["source"] for row in conn.execute("SELECT source FROM tossed_message")}
    assert "outlook" in sources
    assert "teams" in sources
    conn.close()

    store = MaildirStore(sandbox.maildir)
    assert len(store.list_uidls()) >= 1
    assert_log_story(
        caplog,
        [
            {
                "where": "sync.tasks.sync_mailbox",
                "beat": "exit",
                "must_include": ["status=completed"],
            }
        ],
    )
