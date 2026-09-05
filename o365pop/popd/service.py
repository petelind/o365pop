"""Twisted POP3 factory — cleartext USER/PASS, no STLS/APOP."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def run_popd(*, bind: str, port: int, maildir: Path, db_path: Path) -> None:
    """Start the Twisted reactor serving POP3.

    :param bind: Listen address. Example: ``"10.8.0.1"``
    :param port: Listen port. Example: ``110``
    :param maildir: Maildir root. Example: ``Path("var/maildir")``
    :param db_path: sqlite for local password. Example: ``Path("var/o365pop.sqlite3")``
    :return: None (blocks)
    :raises ValueError: if bind is rejected by validate_bind
    """
    logger.info("popd.service.run_popd | entry | bind=%s port=%s", bind, port)
    # 1. validate_bind
    # 2. Portal + checker via verify_local_password
    # 3. POP3 factory, no TLS
    # 4. reactor.listenTCP / reactor.run
    raise NotImplementedError()
