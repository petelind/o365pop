"""CAL — sync_calendar exit published=1 patched= with FileGraphAdapter."""

from __future__ import annotations

import json
import logging
import shutil

import pytest

from o365pop.celery_app import celery_app
from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.sync import tasks as sync_tasks
from tests.support.fixtures import load_graph_case
from tests.support.log_story import assert_log_story
from tests.support.mailbox import MailboxSandbox, open_sandbox_db


class _OkAuth:
    def ensure_bearer(self) -> str:
        return "test-bearer"


@pytest.mark.integration
@pytest.mark.log_story
def test_sync_calendar_log_story_happy(
    sandbox: MailboxSandbox, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Eager sync_calendar publishes the standup snapshot and applies one receipt.

    :param sandbox: Isolated data dirs
    :param monkeypatch: Env and factory overrides
    :param caplog: pytest log capture
    :return: None
    """
    caplog.set_level(logging.INFO)
    open_sandbox_db(sandbox).close()
    case = sandbox.root / "graph-case"
    shutil.copytree(load_graph_case("CAL1.1-standup"), case)
    dest = sandbox.root / "calendar" / "snapshot.json"
    monkeypatch.setenv("DATA_DIR", str(sandbox.root))
    monkeypatch.setenv("DB_PATH", str(sandbox.db_path))
    monkeypatch.setenv("LOG_DIR", str(sandbox.log_dir))
    monkeypatch.setenv("CAL_SNAPSHOT_PATH", str(dest))
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "1")
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    new_dir = dest.parent / "receipts" / "new"
    new_dir.mkdir(parents=True)
    (new_dir / "evt-standup.json").write_text(
        json.dumps(
            {
                "uid": "evt-standup",
                "subject": "Standup moved",
                "location": "Room B",
                "reminderMinutesBeforeStart": 10,
                "showAs": "tentative",
                "sensitivity": "private",
                "deleted": False,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(sync_tasks, "auth_service_factory", lambda conn, settings: _OkAuth())
    monkeypatch.setattr(sync_tasks, "graph_factory", lambda settings, token: FileGraphAdapter(case))
    result = sync_tasks.sync_calendar.apply()
    assert result.successful()
    assert result.result["status"] == "completed"
    assert result.result["published"] == 1
    assert result.result["patched"] == 1
    assert dest.is_file()
    assert_log_story(
        caplog,
        where="sync.tasks.sync_calendar",
        beats={"exit": ["published=1", "patched="]},
    )
