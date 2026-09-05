"""Celery tasks: AUTH + SYNC inbound; SMTP/TEAM extend (do not add a second mailbox task)."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable

import httpx
from celery.exceptions import SoftTimeLimitExceeded

from o365pop.accounts.errors import AuthenticationError
from o365pop.accounts.graph_auth import GraphAuthService, live_device_code_port, live_msal_port
from o365pop.celery_app import celery_app
from o365pop.config import Settings, load_settings
from o365pop.db import connect, init_schema
from o365pop.graph.http_adapter import HttpGraphAdapter
from o365pop.graph.port import GraphPort
from o365pop.mailstore.maildir import MaildirStore
from o365pop.sync.sessions import SyncSession, mark_completed, mark_failed, start_session
from o365pop.tosser.inbound import InboundTosser

logger = logging.getLogger(__name__)

AuthFactory = Callable[..., GraphAuthService]
GraphFactory = Callable[..., GraphPort]
auth_service_factory: AuthFactory | None = None
graph_factory: GraphFactory | None = None


@celery_app.task(bind=True, name="o365pop.sync.sync_mailbox")
def sync_mailbox(self) -> dict:
    """Ensure bearer, toss inbox+chats, mark session. Auth fail does not retry.

    :return: Result dict. Example: ``{"status": "completed", "error": None, "tossed": 1}``
    """
    task_id = getattr(self.request, "id", None)
    logger.info("sync.tasks.sync_mailbox | entry | task_id=%s", task_id)
    settings = load_settings()
    conn = connect(settings.db_path)
    init_schema(conn)
    session = start_session(conn, str(task_id) if task_id else None)
    try:
        return _run_inbound_sync(conn, settings, session)
    except AuthenticationError:
        return _fail_closed(conn, session, "auth_failed")
    except (SoftTimeLimitExceeded, TimeoutError, httpx.TimeoutException):
        return _fail_closed(conn, session, "timeout")
    except Exception:
        logger.exception("sync.tasks.sync_mailbox | error | reason=sync_failed session_id=%s", session.session_id)
        return _fail_closed(conn, session, "sync_failed")


@celery_app.task(bind=True, name="o365pop.sync.scan_outbound_spool")
def scan_outbound_spool(self) -> dict:
    """SMTP/TEAM: scan spool and sendMail or post chat.

    :return: Result dict. Example: ``{"status": "completed", "sent": 1}``
    """
    logger.info("sync.tasks.scan_outbound_spool | entry | task_id=%s", getattr(self.request, "id", None))
    raise NotImplementedError()


def _run_inbound_sync(conn: sqlite3.Connection, settings: Settings, session: SyncSession) -> dict:
    """Bearer → Graph pull → toss → completed.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param settings: Loaded settings. Example: ``load_settings()``
    :param session: Running session. Example: ``SyncSession(session_id=1, status="running", error=None)``
    :return: Success dict. Example: ``{"status": "completed", "error": None, "tossed": 0}``
    """
    service = _resolve_auth_service(conn, settings)
    token = service.ensure_bearer()
    graph = _resolve_graph(settings, token)
    maildir = MaildirStore(settings.data_dir / "maildir")
    counts = InboundTosser(conn, maildir, graph).toss_all()
    tossed = int(counts["tossed"])
    mark_completed(conn, session.session_id, tossed=tossed)
    logger.info(
        "sync.tasks.sync_mailbox | exit | status=completed tossed=%s session_id=%s",
        tossed,
        session.session_id,
    )
    return {"status": "completed", "error": None, "tossed": tossed}


def _fail_closed(conn: sqlite3.Connection, session: SyncSession, error: str) -> dict:
    """Mark failed and return; caller must not raise (no Celery retry).

    :param conn: sqlite connection. Example: ``connect(path)``
    :param session: Running session. Example: ``SyncSession(session_id=1, status="running", error=None)``
    :param error: Safe token. Example: ``"auth_failed"``
    :return: Failure dict. Example: ``{"status": "failed", "error": "auth_failed"}``
    """
    mark_failed(conn, session.session_id, error)
    logger.error("sync.tasks.sync_mailbox | error | reason=%s session_id=%s", error, session.session_id)
    logger.info("sync.tasks.sync_mailbox | exit | status=failed")
    return {"status": "failed", "error": error}


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


def _resolve_graph(settings: Settings, access_token: str) -> GraphPort:
    """Build GraphPort from the test factory or live httpx adapter.

    :param settings: Loaded settings. Example: ``load_settings()``
    :param access_token: Bearer. Example: ``"eyJ0..."``
    :return: Graph port. Example: ``HttpGraphAdapter("eyJ0...")``
    """
    if graph_factory is not None:
        logger.info("sync.tasks._resolve_graph | branch | factory=test")
        return graph_factory(settings, access_token)
    logger.info("sync.tasks._resolve_graph | branch | factory=live")
    return HttpGraphAdapter(access_token)
