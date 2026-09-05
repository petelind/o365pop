"""BOOT1.3 — SQLite schema tables exist after init."""

from __future__ import annotations

from pathlib import Path

import pytest

from o365pop.db import REQUIRED_TABLES, connect, init_schema, list_tables


@pytest.mark.unit
def test_init_schema_creates_required_tables(tmp_db_path: Path) -> None:
    """mailbox_account, sync_session, tossed_message, chat_map exist.

    :param tmp_db_path: Isolated SQLite path. Example: ``Path("/tmp/.../o365pop.sqlite3")``
    :return: None
    """
    conn = connect(tmp_db_path)
    try:
        init_schema(conn)
        tables = list_tables(conn)
    finally:
        conn.close()
    assert tmp_db_path.is_file()
    for name in REQUIRED_TABLES:
        assert name in tables


@pytest.mark.unit
def test_init_schema_is_idempotent(tmp_db_path: Path) -> None:
    """Applying the schema twice does not raise.

    :param tmp_db_path: Isolated SQLite path. Example: ``Path("/tmp/.../o365pop.sqlite3")``
    :return: None
    """
    conn = connect(tmp_db_path)
    try:
        init_schema(conn)
        init_schema(conn)
        assert set(REQUIRED_TABLES).issubset(set(list_tables(conn)))
    finally:
        conn.close()
