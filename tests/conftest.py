"""Shared pytest fixtures.

TFK-02 helpers (import these in tests — do not hide them behind autouse):

- ``from tests.support.log_story import assert_log_story``
- ``from tests.support.fixtures import load_graph_case, load_mail, load_preset``
- ``from tests.support.mailbox import mailbox_sandbox, open_sandbox_db, apply_preset``

SAO §17 is N/A: no ``assert_agent_story``, no ``scripted_llm`` fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.mailbox import MailboxSandbox, mailbox_sandbox


@pytest.fixture
def tmp_log_dir(tmp_path: Path) -> Path:
    """Isolated log directory for a single test.

    :param tmp_path: pytest tmp path. Example: ``Path("/tmp/pytest-of-denis/...")``
    :return: ``logs`` subdirectory. Example: ``Path("/tmp/.../logs")``
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Isolated SQLite path for a single test.

    :param tmp_path: pytest tmp path. Example: ``Path("/tmp/pytest-of-denis/...")``
    :return: Database file path (not yet created). Example: ``Path("/tmp/.../data/o365pop.sqlite3")``
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir / "o365pop.sqlite3"


@pytest.fixture
def sandbox(tmp_path: Path) -> MailboxSandbox:
    """Isolated maildir, spool, sqlite, and log dirs.

    :param tmp_path: pytest tmp path. Example: ``Path("/tmp/pytest-...")``
    :return: Sandbox paths. Example: ``MailboxSandbox(root=..., ...)``
    """
    return mailbox_sandbox(tmp_path / "sandbox")
