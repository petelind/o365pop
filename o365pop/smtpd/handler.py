"""aiosmtpd handler: AUTH LOGIN/PLAIN, write spool, never import graph."""

from __future__ import annotations

import logging
from pathlib import Path

from aiosmtpd.smtp import MISSING, AuthResult, LoginPassword

from o365pop.accounts.store import verify_local_password
from o365pop.db import connect
from o365pop.mailstore.spool import SpoolStore

logger = logging.getLogger(__name__)

_AUTH_OK = {"LOGIN", "PLAIN"}


class BridgeHandler:
    """Accept RFC822 into SpoolStore.

    :param spool_root: Spool directory. Example: ``Path("var/spool")``
    :param db_path: sqlite for local AUTH. Example: ``Path("var/o365pop.sqlite3")``
    """

    def __init__(self, spool_root: Path, db_path: Path) -> None:
        self._spool_root = spool_root
        self._db_path = db_path
        self._spool = SpoolStore(spool_root)

    async def handle_AUTH(self, server, session, envelope, *args):
        """Defer AUTH to aiosmtpd LOGIN/PLAIN plus ``_authenticate``.

        :return: ``MISSING`` so builtin AUTH runs. Example: ``MISSING``
        """
        logger.info("BridgeHandler.handle_AUTH | entry | args=%s", _auth_hook_label(args))
        return MISSING

    def _authenticate(self, server, session, envelope, mechanism, auth_data) -> AuthResult:
        """Sync authenticator for aiosmtpd (must not log the password).

        :param server: SMTP protocol. Example: ``<SMTP>``
        :param session: Session. Example: ``<Session>``
        :param envelope: Envelope. Example: ``<Envelope>``
        :param mechanism: AUTH name. Example: ``"LOGIN"``
        :param auth_data: Credentials. Example: ``LoginPassword(b"denis", b"...")``
        :return: Result. Example: ``AuthResult(success=True)``
        """
        mech = str(mechanism or "").upper()
        if mech not in _AUTH_OK or not isinstance(auth_data, LoginPassword):
            logger.error("BridgeHandler.handle_AUTH | error | reason=auth_failed mechanism=%s", mech)
            return AuthResult(success=False, handled=False)
        username = auth_data.login.decode("utf-8")
        password = auth_data.password.decode("utf-8")
        conn = connect(self._db_path)
        try:
            matched = verify_local_password(conn, username, password)
        finally:
            conn.close()
        if not matched:
            logger.error("BridgeHandler.handle_AUTH | error | reason=auth_failed username=%s", username)
            return AuthResult(success=False, handled=False)
        logger.info("BridgeHandler.handle_AUTH | exit | matched=true username=%s", username)
        return AuthResult(success=True, auth_data=auth_data)

    async def handle_DATA(self, server, session, envelope):
        """Write envelope.content to spool/new.

        :return: SMTP reply. Example: ``"250 Message accepted"``
        """
        rcpts = list(getattr(envelope, "rcpt_tos", []) or [])
        logger.info("BridgeHandler.handle_DATA | entry | rcpt_count=%s", len(rcpts))
        if not getattr(session, "authenticated", False):
            logger.error("BridgeHandler.handle_DATA | error | reason=auth_failed")
            return "530 Authentication required"
        content = bytes(getattr(envelope, "content", b"") or b"")
        path = self._spool.enqueue(content)
        logger.info("BridgeHandler.handle_DATA | exit | status=accepted size=%s name=%s", len(content), path.name)
        return "250 Message accepted"


def _auth_hook_label(args: tuple) -> str:
    """Safe AUTH hook summary (never the password).

    :param args: Hook extras. Example: ``(["LOGIN"],)``
    :return: Label. Example: ``"LOGIN"``
    """
    if not args:
        return ""
    first = args[0]
    if isinstance(first, (list, tuple)) and first:
        return str(first[0])
    return str(first)
