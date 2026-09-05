"""Process-start logging to ``logs/app.log`` (SAO §11)."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

APP_LOGGER_NAME = "o365pop"
LOG_FORMAT = "%(name)s | %(message)s"
MAX_BYTES = 10 * 1024 * 1024
BACKUP_COUNT = 5

logger = logging.getLogger(__name__)


def configure_logging(log_dir: Path | None = None) -> Path:
    """Configure rotating ``app.log`` and rotate any prior file on start.

    Format is ``{logger} | {Class.method} | {beat} | key=value`` — callers put
    ``Class.method | beat | key=value`` in the message.

    :param log_dir: Directory for ``app.log``. Example: ``Path("logs")``
    :return: Path to the active log file. Example: ``Path("logs/app.log")``
    :raises OSError: if the log directory cannot be created
    """
    resolved = Path(log_dir) if log_dir is not None else Path("logs")
    resolved.mkdir(parents=True, exist_ok=True)
    log_path = resolved / "app.log"
    _rotate_on_start(log_path)
    _reset_app_handlers()
    handler = RotatingFileHandler(
        log_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    app_logger = logging.getLogger(APP_LOGGER_NAME)
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(handler)
    app_logger.propagate = False
    # Package modules use ``o365pop.*`` loggers
    package_logger = logging.getLogger("o365pop")
    if package_logger is not app_logger:
        package_logger.setLevel(logging.INFO)
        package_logger.addHandler(handler)
        package_logger.propagate = False
    logger.info(
        "logging_setup.configure_logging | exit | log_path=%s max_bytes=%s backups=%s",
        log_path,
        MAX_BYTES,
        BACKUP_COUNT,
    )
    return log_path


def _rotate_on_start(log_path: Path) -> None:
    """Move an existing non-empty ``app.log`` aside so this process starts clean.

    :param log_path: Active log file. Example: ``Path("logs/app.log")``
    :return: None
    """
    if not log_path.exists() or log_path.stat().st_size == 0:
        return
    backup = log_path.with_name("app.log.1")
    if backup.exists():
        backup.unlink()
    log_path.replace(backup)


def _reset_app_handlers() -> None:
    """Drop existing file handlers so tests and relaunches do not stack.

    :return: None
    """
    for name in (APP_LOGGER_NAME, "o365pop"):
        target = logging.getLogger(name)
        for handler in list(target.handlers):
            if isinstance(handler, RotatingFileHandler):
                target.removeHandler(handler)
                handler.close()
