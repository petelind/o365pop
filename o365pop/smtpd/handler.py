"""aiosmtpd handler: AUTH LOGIN/PLAIN, write spool, never import graph."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class BridgeHandler:
    """Accept RFC822 into SpoolStore.

    :param spool_root: Spool directory. Example: ``Path("var/spool")``
    :param db_path: sqlite for local AUTH. Example: ``Path("var/o365pop.sqlite3")``
    """

    def __init__(self, spool_root: Path, db_path: Path) -> None:
        self._spool_root = spool_root
        self._db_path = db_path

    async def handle_AUTH(self, server, session, envelope, mechanism, auth_data):
        """AUTH LOGIN or PLAIN.

        :return: Auth result. Example: ``AuthResult(success=True)``
        """
        logger.info("BridgeHandler.handle_AUTH | entry | mechanism=%s", mechanism)
        raise NotImplementedError()

    async def handle_DATA(self, server, session, envelope):
        """Write envelope.content to spool/new.

        :return: SMTP reply. Example: ``"250 Message accepted"``
        """
        logger.info("BridgeHandler.handle_DATA | entry | rcpt_count=%s", len(getattr(envelope, "rcpt_tos", [])))
        raise NotImplementedError()
