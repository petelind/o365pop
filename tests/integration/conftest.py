"""Integration-layer fixtures — real sqlite/maildir; Celery eager.

No ``unittest.mock`` on domain services. Graph uses ``FileGraphAdapter`` fixtures.
"""

from __future__ import annotations

import pytest

from tests.support.mailbox import MailboxSandbox


@pytest.fixture
def eager_celery(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force Celery to run tasks in-process (SAO §15).

    :param monkeypatch: pytest monkeypatch
    :return: None
    """
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "1")


@pytest.fixture
def isolated_env(sandbox: MailboxSandbox, monkeypatch: pytest.MonkeyPatch) -> MailboxSandbox:
    """Point process env at the sandbox (AUTH/SYNC/POP/SMTP tests).

    :param sandbox: Isolated paths
    :param monkeypatch: pytest monkeypatch
    :return: The same sandbox
    """
    monkeypatch.setenv("DATA_DIR", str(sandbox.root / "data"))
    monkeypatch.setenv("DB_PATH", str(sandbox.db_path))
    monkeypatch.setenv("LOG_DIR", str(sandbox.log_dir))
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "1")
    return sandbox
