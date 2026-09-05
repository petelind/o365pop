"""sync_session row helpers (taciturn2 job status shape)."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass

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
    raise NotImplementedError()


def mark_completed(conn: sqlite3.Connection, session_id: int, *, tossed: int = 0, sent: int = 0) -> SyncSession:
    """Mark a session completed.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param session_id: Row id. Example: ``1``
    :param tossed: Inbound count. Example: ``3``
    :param sent: Outbound count. Example: ``1``
    :return: Updated session. Example: ``SyncSession(..., status="completed")``
    """
    logger.info("sync.sessions.mark_completed | entry | session_id=%s tossed=%s sent=%s", session_id, tossed, sent)
    raise NotImplementedError()


def mark_failed(conn: sqlite3.Connection, session_id: int, error: str) -> SyncSession:
    """Mark a session failed. Caller must not enqueue a retry.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param session_id: Row id. Example: ``1``
    :param error: Safe token. Example: ``"auth_failed"``
    :return: Updated session. Example: ``SyncSession(..., status="failed")``
    """
    logger.info("sync.sessions.mark_failed | entry | session_id=%s error=%s", session_id, error)
    raise NotImplementedError()
