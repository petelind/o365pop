"""Celery tasks: AUTH stub first; SYNC/SMTP/TEAM extend (do not add a second mailbox task)."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable

from o365pop.accounts.errors import AuthenticationError
from o365pop.accounts.graph_auth import GraphAuthService, live_device_code_port, live_msal_port
from o365pop.celery_app import celery_app
from o365pop.config import Settings, load_settings
from o365pop.db import connect, init_schema
from o365pop.sync.sessions import mark_completed, mark_failed, start_session

logger = logging.getLogger(__name__)

AuthFactory = Callable[..., GraphAuthService]
auth_service_factory: AuthFactory | None = None


@celery_app.task(bind=True, name="o365pop.sync.sync_mailbox")
def sync_mailbox(self) -> dict:
    """Ensure bearer then (later) pull+toss. Auth fail → failed session, no retry.

    :return: Result dict. Example: ``{"status": "failed", "error": "auth_failed"}``
    """
    task_id = getattr(self.request, "id", None)
    logger.info("sync.tasks.sync_mailbox | entry | task_id=%s", task_id)
    settings = load_settings()
    conn = connect(settings.db_path)
    init_schema(conn)
    session = start_session(conn, str(task_id) if task_id else None)
    try:
        service = _resolve_auth_service(conn, settings)
        service.ensure_bearer()
    except AuthenticationError:
        mark_failed(conn, session.session_id, "auth_failed")
        logger.error("sync.tasks.sync_mailbox | error | reason=auth_failed session_id=%s", session.session_id)
        logger.info("sync.tasks.sync_mailbox | exit | status=failed")
        return {"status": "failed", "error": "auth_failed"}
    mark_completed(conn, session.session_id)
    logger.info("sync.tasks.sync_mailbox | exit | status=completed session_id=%s", session.session_id)
    return {"status": "completed", "error": None}


@celery_app.task(bind=True, name="o365pop.sync.scan_outbound_spool")
def scan_outbound_spool(self) -> dict:
    """SMTP/TEAM: scan spool and sendMail or post chat.

    :return: Result dict. Example: ``{"status": "completed", "sent": 1}``
    """
    logger.info("sync.tasks.scan_outbound_spool | entry | task_id=%s", getattr(self.request, "id", None))
    raise NotImplementedError()


def _resolve_auth_service(conn: sqlite3.Connection, settings: Settings) -> GraphAuthService:
    """Build GraphAuthService from the test factory or live MSAL ports.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param settings: Loaded settings. Example: ``load_settings()``
    :return: Auth service. Example: ``GraphAuthService(...)``
    """
    if auth_service_factory is not None:
        logger.info("sync.tasks._resolve_auth_service | branch | factory=test")
        return auth_service_factory(conn, settings)
    logger.info("sync.tasks._resolve_auth_service | branch | factory=live")
    return GraphAuthService(
        conn,
        settings.token_encryption_key,
        live_device_code_port(settings.azure_client_id, settings.azure_tenant_id),
        live_msal_port(settings.azure_client_id, settings.azure_tenant_id),
    )
