"""aiosmtpd process — no STARTTLS."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def run_smtpd(*, bind: str, port: int, spool_root: Path, db_path: Path) -> None:
    """Start aiosmtpd on bind:port.

    :param bind: Listen address. Example: ``"10.8.0.1"``
    :param port: Listen port. Example: ``587``
    :param spool_root: Spool directory. Example: ``Path("var/spool")``
    :param db_path: sqlite path. Example: ``Path("var/o365pop.sqlite3")``
    :return: None (blocks)
    :raises ValueError: if bind is rejected
    """
    logger.info("smtpd.service.run_smtpd | entry | bind=%s port=%s", bind, port)
    raise NotImplementedError()
