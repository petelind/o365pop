"""Start real popd / wait for TCP during live journey tests."""

from __future__ import annotations

import logging
import socket
import time
from multiprocessing import Process
from pathlib import Path

from tests.support.live_session import LiveSession

logger = logging.getLogger(__name__)

POP_HOST = "127.0.0.1"
LIVE_POP_PORT = 12110


def wait_port(host: str, port: int, timeout: float = 8.0) -> None:
    """Block until TCP accept works.

    :param host: Address. Example: ``"127.0.0.1"``
    :param port: Port. Example: ``12110``
    :param timeout: Seconds. Example: ``8.0``
    :return: None
    :raises TimeoutError: if the port never opens
    """
    logger.info("live_daemons.wait_port | entry | host=%s port=%s", host, port)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                logger.info("live_daemons.wait_port | exit | status=open")
                return
        except OSError:
            time.sleep(0.05)
    logger.error("live_daemons.wait_port | error | reason=timeout host=%s port=%s", host, port)
    raise TimeoutError(f"{host}:{port} did not open")


def start_live_popd(session: LiveSession, port: int = LIVE_POP_PORT) -> Process:
    """Spawn Twisted popd against the captured vault.

    :param session: Captured session. Example: result of ``ensure_captured_session()``
    :param port: Listen port. Example: ``12110``
    :return: Child process. Example: ``<Process>``
    """
    logger.info("live_daemons.start_live_popd | entry | port=%s", port)
    maildir = session.settings.data_dir / "maildir"
    proc = Process(
        target=_run_popd_process,
        args=(POP_HOST, port, str(maildir), str(session.settings.db_path), str(session.settings.log_dir)),
        daemon=True,
    )
    proc.start()
    wait_port(POP_HOST, port)
    logger.info("live_daemons.start_live_popd | exit | pid=%s", proc.pid)
    return proc


def stop_live_popd(proc: Process) -> None:
    """Terminate the child popd.

    :param proc: Process from start_live_popd. Example: ``<Process>``
    :return: None
    """
    logger.info("live_daemons.stop_live_popd | entry | pid=%s", proc.pid)
    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=5)
    logger.info("live_daemons.stop_live_popd | exit | alive=%s", proc.is_alive())


def _run_popd_process(bind: str, port: int, maildir: str, db_path: str, log_dir: str) -> None:
    """Child process: block on Twisted reactor.

    :param bind: Listen address. Example: ``"127.0.0.1"``
    :param port: Listen port. Example: ``12110``
    :param maildir: Maildir path. Example: ``"var/live-e2e/maildir"``
    :param db_path: sqlite path. Example: ``"var/live-e2e/o365pop.sqlite3"``
    :param log_dir: Child app.log directory. Example: ``"var/live-e2e/logs"``
    :return: None
    """
    from o365pop.logging_setup import configure_logging
    from o365pop.popd.service import run_popd

    configure_logging(Path(log_dir))
    run_popd(bind=bind, port=port, maildir=Path(maildir), db_path=Path(db_path))
