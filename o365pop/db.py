"""SQLite connection and schema bootstrap (SAO §4)."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
REQUIRED_TABLES = ("mailbox_account", "sync_session", "tossed_message", "chat_map")


def connect(db_path: Path | str) -> sqlite3.Connection:
    """Open a SQLite connection, creating parent directories as needed.

    :param db_path: Database file. Example: ``Path("var/o365pop.sqlite3")``
    :return: Connection with ``Row`` factory. Example: ``<sqlite3.Connection>``
    :raises OSError: if the parent directory cannot be created
    """
    path = Path(db_path)
    logger.info("db.connect | entry | db_path=%s", path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    logger.info("db.connect | exit | db_path=%s", path)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Apply ``schema.sql`` to an open connection.

    :param conn: SQLite connection. Example: result of ``connect(...)``
    :return: None
    :raises FileNotFoundError: if ``schema.sql`` is missing
    :raises sqlite3.Error: if the script fails
    """
    logger.info("db.init_schema | entry | schema=%s", SCHEMA_PATH)
    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError(f"schema.sql not found at {SCHEMA_PATH}")
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()
    present = list_tables(conn)
    logger.info("db.init_schema | exit | tables=%s", present)


def list_tables(conn: sqlite3.Connection) -> list[str]:
    """Return user table names in the database.

    :param conn: SQLite connection. Example: result of ``connect(...)``
    :return: Sorted table names. Example: ``["chat_map", "mailbox_account"]``
    """
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return sorted(str(row["name"]) for row in rows)
