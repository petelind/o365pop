"""sync_session row helpers (taciturn2 job status shape)."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SyncSession:
    """One Celery run.

    :param session_id: sqlite id. Example: ``1``
    :param status: pending|running|completed|failed. Example: ``"failed"``
    :param error: Safe error token. Example: ``"auth_failed"``
    """

    session_id: int
    status: str
    error: str | None


def start_session(conn: sqlite3.Connection, celery_task_id: str | None = None) -> SyncSession:
    """Insert a running session.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param celery_task_id: Celery id. Example: ``"abc-123"``
    :return: New session. Example: ``SyncSession(session_id=1, status="running", error=None)``
    """
    logger.info("sync.sessions.start_session | entry | celery_task_id=%s", celery_task_id)
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    cursor = conn.execute(
        """
        INSERT INTO sync_session (started_at, status, celery_task_id)
        VALUES (?, 'running', ?)
        """,
        (now, celery_task_id),
    )
    conn.commit()
    session = SyncSession(session_id=int(cursor.lastrowid), status="running", error=None)
    logger.info("sync.sessions.start_session | exit | session_id=%s", session.session_id)
    return session


def mark_completed(conn: sqlite3.Connection, session_id: int, *, tossed: int = 0, sent: int = 0) -> SyncSession:
    """Mark a session completed.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param session_id: Row id. Example: ``1``
    :param tossed: Inbound count. Example: ``3``
    :param sent: Outbound count. Example: ``1``
    :return: Updated session. Example: ``SyncSession(..., status="completed")``
    """
    logger.info("sync.sessions.mark_completed | entry | session_id=%s tossed=%s sent=%s", session_id, tossed, sent)
    return _finish(conn, session_id, "completed", None, tossed=tossed, sent=sent)


def mark_failed(conn: sqlite3.Connection, session_id: int, error: str) -> SyncSession:
    """Mark a session failed. Caller must not enqueue a retry.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param session_id: Row id. Example: ``1``
    :param error: Safe token. Example: ``"auth_failed"``
    :return: Updated session. Example: ``SyncSession(..., status="failed")``
    """
    logger.info("sync.sessions.mark_failed | entry | session_id=%s error=%s", session_id, error)
    return _finish(conn, session_id, "failed", error)


def _finish(
    conn: sqlite3.Connection,
    session_id: int,
    status: str,
    error: str | None,
    *,
    tossed: int = 0,
    sent: int = 0,
) -> SyncSession:
    """Write finished_at and status.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param session_id: Row id. Example: ``1``
    :param status: completed|failed. Example: ``"failed"``
    :param error: Safe token or None. Example: ``"auth_failed"``
    :param tossed: Inbound count. Example: ``0``
    :param sent: Outbound count. Example: ``0``
    :return: Updated session. Example: ``SyncSession(..., status="failed")``
    """
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    conn.execute(
        """
        UPDATE sync_session
        SET finished_at = ?, status = ?, error = ?, messages_tossed = ?, messages_sent = ?
        WHERE id = ?
        """,
        (now, status, error, tossed, sent, session_id),
    )
    conn.commit()
    session = SyncSession(session_id=session_id, status=status, error=error)
    logger.info("sync.sessions._finish | exit | session_id=%s status=%s", session_id, status)
    return session
