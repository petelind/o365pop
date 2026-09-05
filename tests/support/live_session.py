"""Capture one Microsoft device-code login and reuse it for live journey tests.

Tokens stay Fernet-encrypted under ``var/live-e2e/`` (gitignored). Never log
tokens, mailbox passwords, device codes, or raw MIME.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
import time
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

import httpx
from dotenv import load_dotenv

from o365pop.accounts.graph_auth import GraphAuthService, live_device_code_port, live_msal_port
from o365pop.accounts.store import (
    get_account,
    get_encrypted_refresh_token,
)
from o365pop.cli import _apply_local_mailbox
from o365pop.config import Settings, load_settings
from o365pop.db import connect, init_schema
from o365pop.graph.http_adapter import GRAPH_ROOT, HttpGraphAdapter

logger = logging.getLogger(__name__)

LIVE_HOME = Path("var/live-e2e")
GRAPH_POLL_ATTEMPTS = 12
GRAPH_POLL_SECONDS = 2.0


@dataclass(frozen=True)
class LiveSession:
    """Captured operator mailbox for live journey tests.

    :param settings: Settings bound to ``var/live-e2e``. Example: ``load_settings()``
    :param username: Graph UPN. Example: ``"denis@contoso.com"``
    :param mailbox_user: Local POP/SMTP USER. Example: ``"denis"``
    :param mailbox_password: Local POP/SMTP PASS (not Microsoft). Example: ``"local-only"``
    :param home: Live data root. Example: ``Path("var/live-e2e")``
    """

    settings: Settings
    username: str
    mailbox_user: str
    mailbox_password: str
    home: Path


def live_env_skip_reason() -> str | None:
    """Why live tests cannot run, or None when env is complete.

    :return: Skip text or None. Example: ``"AZURE_CLIENT_ID is required"``
    """
    logger.info("live_session.live_env_skip_reason | entry")
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
    missing: list[str] = []
    if not os.getenv("AZURE_CLIENT_ID"):
        missing.append("AZURE_CLIENT_ID")
    if not os.getenv("TOKEN_ENCRYPTION_KEY"):
        missing.append("TOKEN_ENCRYPTION_KEY")
    if not os.getenv("MAILBOX_USER"):
        missing.append("MAILBOX_USER")
    if not os.getenv("MAILBOX_PASSWORD"):
        missing.append("MAILBOX_PASSWORD")
    reason = None
    if missing:
        reason = "live journey needs " + ", ".join(missing)
        logger.info("live_session.live_env_skip_reason | branch | ready=false missing=%s", ",".join(missing))
    else:
        logger.info("live_session.live_env_skip_reason | branch | ready=true")
    logger.info("live_session.live_env_skip_reason | exit | skip=%s", reason is not None)
    return reason


def bind_live_home(home: Path) -> None:
    """Point DATA_DIR / DB_PATH / LOG_DIR at the live vault.

    :param home: Vault root. Example: ``Path("var/live-e2e")``
    :return: None
    """
    logger.info("live_session.bind_live_home | entry | home=%s", home)
    home.mkdir(parents=True, exist_ok=True)
    (home / "logs").mkdir(exist_ok=True)
    for folder in ("cur", "new", "tmp"):
        (home / "maildir" / folder).mkdir(parents=True, exist_ok=True)
    for folder in ("new", "retry", "sent", "failed"):
        (home / "spool" / folder).mkdir(parents=True, exist_ok=True)
    os.environ["DATA_DIR"] = str(home)
    os.environ["DB_PATH"] = str(home / "o365pop.sqlite3")
    os.environ["LOG_DIR"] = str(home / "logs")
    logger.info("live_session.bind_live_home | exit | db_path=%s", home / "o365pop.sqlite3")


def ensure_captured_session(home: Path = LIVE_HOME) -> LiveSession:
    """Reuse encrypted tokens, or run device-code login once.

    Prints the Microsoft user code to stdout when capture is needed (run pytest ``-s``).

    :param home: Vault root. Example: ``Path("var/live-e2e")``
    :return: Session. Example: ``LiveSession(username="denis@contoso.com", ...)``
    :raises ValueError: if required env is missing
    """
    logger.info("live_session.ensure_captured_session | entry | home=%s", home)
    reason = live_env_skip_reason()
    if reason:
        raise ValueError(reason)
    bind_live_home(home)
    settings = load_settings()
    conn = connect(settings.db_path)
    try:
        init_schema(conn)
        _apply_local_mailbox(conn, settings)
        username = _login_or_refresh(conn, settings)
        _apply_local_mailbox(conn, settings)
        account = get_account(conn)
    finally:
        conn.close()
    from_account = account.mailbox_user if account and account.mailbox_user else None
    mailbox_user = from_account or settings.mailbox_user or username.split("@")[0]
    session = LiveSession(
        settings=settings,
        username=username,
        mailbox_user=mailbox_user,
        mailbox_password=settings.mailbox_password,
        home=home,
    )
    logger.info(
        "live_session.ensure_captured_session | exit | user=%s mailbox_user=%s",
        session.username,
        session.mailbox_user,
    )
    return session


def open_live_db(session: LiveSession) -> sqlite3.Connection:
    """Open the captured vault sqlite.

    :param session: Captured session. Example: result of ``ensure_captured_session()``
    :return: Connection. Example: ``<sqlite3.Connection>``
    """
    logger.info("live_session.open_live_db | entry | db_path=%s", session.settings.db_path)
    conn = connect(session.settings.db_path)
    init_schema(conn)
    logger.info("live_session.open_live_db | exit | status=ok")
    return conn


def live_bearer(session: LiveSession, conn: sqlite3.Connection) -> str:
    """Refreshed access token. Caller must not log it.

    :param session: Captured session. Example: result of ``ensure_captured_session()``
    :param conn: Open vault sqlite. Example: ``open_live_db(session)``
    :return: Bearer. Example: ``"eyJ0..."``
    """
    logger.info("live_session.live_bearer | entry | user=%s", session.username)
    token = _auth_service(conn, session.settings).ensure_bearer()
    logger.info("live_session.live_bearer | exit | token_len=%s", len(token))
    return token


def live_graph(session: LiveSession, conn: sqlite3.Connection) -> HttpGraphAdapter:
    """HttpGraphAdapter with a refreshed bearer.

    :param session: Captured session. Example: result of ``ensure_captured_session()``
    :param conn: Open vault sqlite. Example: ``open_live_db(session)``
    :return: Live adapter. Example: ``HttpGraphAdapter("eyJ0...")``
    """
    logger.info("live_session.live_graph | entry | user=%s", session.username)
    token = live_bearer(session, conn)
    logger.info("live_session.live_graph | exit | token_len=%s", len(token))
    return HttpGraphAdapter(token)


def build_probe_rfc822(*, subject: str, from_addr: str, to_addr: str, body: str) -> bytes:
    """RFC822 used as a live sendMail / SMTP probe.

    :param subject: Unique subject. Example: ``"o365pop-live-abcd"``
    :param from_addr: From. Example: ``"denis@contoso.com"``
    :param to_addr: To. Example: ``"denis@contoso.com"``
    :param body: Plain body. Example: ``"probe"``
    :return: Bytes. Example: ``b"Subject: o365pop-live-abcd\\r\\n..."``
    """
    logger.info("live_session.build_probe_rfc822 | entry | subject=%s size_hint=%s", subject, len(body))
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = to_addr
    message.set_content(body)
    raw = message.as_bytes()
    logger.info("live_session.build_probe_rfc822 | exit | size=%s", len(raw))
    return raw


def wait_inbox_subject(graph: HttpGraphAdapter, subject: str) -> dict:
    """Poll Graph Inbox until subject appears.

    :param graph: Live adapter. Example: ``HttpGraphAdapter(token)``
    :param subject: Probe subject. Example: ``"o365pop-live-abcd"``
    :return: Graph message dict. Example: ``{"id": "AAMk-1", "subject": "o365pop-live-abcd"}``
    :raises TimeoutError: if the message never arrives
    """
    logger.info("live_session.wait_inbox_subject | entry | subject=%s", subject)
    token = graph._access_token
    for attempt in range(1, GRAPH_POLL_ATTEMPTS + 1):
        row = _inbox_by_subject(token, subject)
        if row:
            logger.info(
                "live_session.wait_inbox_subject | exit | found=true attempt=%s graph_id_len=%s",
                attempt,
                len(str(row.get("id") or "")),
            )
            return row
        logger.info("live_session.wait_inbox_subject | processing | attempt=%s found=false", attempt)
        time.sleep(GRAPH_POLL_SECONDS)
    logger.error("live_session.wait_inbox_subject | error | reason=probe_timeout subject=%s", subject)
    raise TimeoutError(f"inbox probe not found: {subject}")


def first_chat_id(graph: HttpGraphAdapter) -> str | None:
    """LIVE_TEAMS_CHAT_ID or the first /me/chats id.

    :param graph: Live adapter. Example: ``HttpGraphAdapter(token)``
    :return: Chat id or None. Example: ``"19:general@thread.v2"``
    """
    configured = os.getenv("LIVE_TEAMS_CHAT_ID", "").strip()
    logger.info("live_session.first_chat_id | entry | env_set=%s", bool(configured))
    if configured:
        logger.info("live_session.first_chat_id | exit | source=env")
        return configured
    payload = _graph_json(graph._access_token, "/me/chats?$top=5")
    rows = list(payload.get("value") or [])
    chat_id = str(rows[0].get("id") or "") if rows else ""
    logger.info("live_session.first_chat_id | exit | source=graph found=%s", bool(chat_id))
    return chat_id or None


def _login_or_refresh(conn: sqlite3.Connection, settings: Settings) -> str:
    """Refresh when a vault exists; otherwise device-code login.

    :param conn: Vault sqlite. Example: ``connect(path)``
    :param settings: Live settings. Example: ``load_settings()``
    :return: Graph UPN. Example: ``"denis@contoso.com"``
    """
    service = _auth_service(conn, settings)
    existing = get_encrypted_refresh_token(conn, settings.token_encryption_key)
    if existing:
        logger.info("live_session._login_or_refresh | branch | capture=reuse")
        service.ensure_bearer()
        account = get_account(conn)
        username = (account.display_name if account and account.display_name else "") or settings.mailbox_user
        logger.info("live_session._login_or_refresh | exit | mode=reuse user=%s", username)
        return username
    logger.info("live_session._login_or_refresh | branch | capture=device_code")
    sys.stderr.write(
        "\nNo saved live session in var/live-e2e/. "
        "Microsoft will print a URL and a short code next — open the URL, enter the code.\n\n"
    )
    sys.stderr.flush()
    username = service.login_device_code()
    logger.info("live_session._login_or_refresh | exit | mode=device_code user=%s", username)
    return username


def _auth_service(conn: sqlite3.Connection, settings: Settings) -> GraphAuthService:
    """Live MSAL GraphAuthService.

    :param conn: Vault sqlite. Example: ``connect(path)``
    :param settings: Live settings. Example: ``load_settings()``
    :return: Service. Example: ``GraphAuthService(...)``
    """
    return GraphAuthService(
        conn,
        settings.token_encryption_key,
        live_device_code_port(settings.azure_client_id, settings.azure_tenant_id),
        live_msal_port(settings.azure_client_id, settings.azure_tenant_id),
    )


def _inbox_by_subject(access_token: str, subject: str) -> dict | None:
    """GET inbox messages filtered by subject.

    :param access_token: Bearer. Example: ``"eyJ0..."``
    :param subject: Exact subject. Example: ``"o365pop-live-abcd"``
    :return: First match or None. Example: ``{"id": "AAMk-1"}``
    """
    escaped = subject.replace("'", "''")
    path = f"/me/mailFolders/inbox/messages?$filter=subject eq '{escaped}'&$top=5"
    payload = _graph_json(access_token, path)
    rows = list(payload.get("value") or [])
    return rows[0] if rows else None


def _graph_json(access_token: str, path: str) -> dict:
    """GET one Graph JSON resource. Never logs the bearer.

    :param access_token: Bearer. Example: ``"eyJ0..."``
    :param path: Absolute path. Example: ``"/me/chats?$top=5"``
    :return: Parsed object. Example: ``{"value": []}``
    """
    logger.info("live_session._graph_json | entry | path=%s", path.split("?")[0])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = httpx.get(f"{GRAPH_ROOT}{path}", headers=headers, timeout=30.0)
    response.raise_for_status()
    payload = response.json()
    logger.info("live_session._graph_json | exit | status=%s", response.status_code)
    return payload if isinstance(payload, dict) else {"value": []}
