"""aiosmtpd process — no STARTTLS."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from threading import Event

from aiosmtpd.controller import Controller

from o365pop.config import validate_bind
from o365pop.smtpd.handler import BridgeHandler

logger = logging.getLogger(__name__)


def run_smtpd(*, bind: str, port: int, spool_root: Path, db_path: Path) -> None:
    """Start aiosmtpd on bind:port.

    :param bind: Listen address. Example: ``"10.8.0.1"``
    :param port: Listen port. Example: ``587``
    :param spool_root: Spool directory. Example: ``Path("var/spool")``
    :param db_path: sqlite path. Example: ``Path("var/o365pop.sqlite3")``
    :return: None (blocks)
    :raises ValueError: if bind is empty
    """
    logger.info("smtpd.service.run_smtpd | entry | bind=%s port=%s", bind, port)
    allow_lan = _allow_lan_from_env()
    validate_bind(bind, allow_lan=allow_lan)
    logger.info("smtpd.service.run_smtpd | config | bind=%s port=%s", bind, port)
    controller = _make_controller(bind=bind, port=port, spool_root=spool_root, db_path=db_path)
    controller.start()
    logger.info("smtpd.service.run_smtpd | exit | listening=true bind=%s port=%s tls=false", bind, port)
    try:
        Event().wait()
    finally:
        controller.stop()


def _allow_lan_from_env() -> bool:
    """Read ALLOW_LAN from the process environment.

    :return: True when ALLOW_LAN is 1/true/TRUE. Example: ``False``
    """
    return os.getenv("ALLOW_LAN", "0") in ("1", "true", "TRUE")


def _make_controller(*, bind: str, port: int, spool_root: Path, db_path: Path) -> Controller:
    """Build a cleartext AUTH LOGIN controller (no STARTTLS).

    :param bind: Listen address. Example: ``"127.0.0.1"``
    :param port: Listen port. Example: ``10587``
    :param spool_root: Spool directory. Example: ``Path("var/spool")``
    :param db_path: sqlite path. Example: ``Path("var/o365pop.sqlite3")``
    :return: Controller. Example: ``<Controller>``
    """
    handler = BridgeHandler(spool_root, db_path)
    logger.info("smtpd.service._make_controller | config | tls=false auth_required=true")
    return Controller(
        handler,
        hostname=bind,
        port=port,
        authenticator=handler._authenticate,
        auth_required=True,
        auth_require_tls=False,
        ident="o365pop",
    )
