"""Environment-backed settings (SAO §12)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from the environment.

    :param azure_client_id: Public MSAL client id. Example: ``"11111111-2222-3333-4444-555555555555"``
    :param azure_tenant_id: Tenant or ``common``. Example: ``"common"``
    :param token_encryption_key: Fernet key for Graph tokens. Example: ``"gAAAAA..."``
    :param mailbox_user: Local POP/SMTP user. Example: ``"denis"``
    :param mailbox_password: Local POP/SMTP password (never the Microsoft password). Example: ``"local-only"``
    :param pop3_bind: POP bind address. Example: ``"10.8.0.1"``
    :param pop3_port: POP port. Example: ``110``
    :param smtp_bind: SMTP bind address. Example: ``"10.8.0.1"``
    :param smtp_port: SMTP port. Example: ``587``
    :param allow_lan: Bind on LAN if true. Example: ``False``
    :param celery_broker_url: Redis broker URL. Example: ``"redis://localhost:6379/0"``
    :param celery_result_backend: Redis result URL. Example: ``"redis://localhost:6379/0"``
    :param graph_poll_seconds: Inbound beat interval. Example: ``120``
    :param spool_scan_seconds: Outbound beat interval. Example: ``30``
    :param task_snapshot_seconds: Task snapshot beat interval. Example: ``60``
    :param task_snapshot_path: Published snapshot file. Example: ``Path("var/tasks/snapshot.json")``
    :param cal_snapshot_seconds: Calendar snapshot beat interval. Example: ``60``
    :param cal_snapshot_path: Published calendar snapshot. Example: ``Path("var/calendar/snapshot.json")``
    :param cal_window_past_days: calendarView past window. Example: ``30``
    :param cal_window_future_days: calendarView future window. Example: ``180``
    :param data_dir: SQLite / maildir parent. Example: ``Path("var")``
    :param db_path: SQLite file. Example: ``Path("var/o365pop.sqlite3")``
    :param log_dir: Log directory. Example: ``Path("logs")``
    """

    azure_client_id: str
    azure_tenant_id: str
    token_encryption_key: str
    mailbox_user: str
    mailbox_password: str
    pop3_bind: str
    pop3_port: int
    smtp_bind: str
    smtp_port: int
    allow_lan: bool
    celery_broker_url: str
    celery_result_backend: str
    graph_poll_seconds: int
    spool_scan_seconds: int
    task_snapshot_seconds: int
    task_snapshot_path: Path
    cal_snapshot_seconds: int
    cal_snapshot_path: Path
    cal_window_past_days: int
    cal_window_future_days: int
    data_dir: Path
    db_path: Path
    log_dir: Path


def load_settings(env_file: Path | None = None) -> Settings:
    """Load settings from ``.env`` and the process environment.

    :param env_file: Optional dotenv path. Example: ``Path(".env")``
    :return: Frozen settings. Example: ``Settings(azure_tenant_id="common", ...)``
    :raises ValueError: if a numeric env var is not an int
    """
    load_dotenv(env_file or _PROJECT_ROOT / ".env", override=False)
    logger.info("config.load_settings | entry | env_file=%s", env_file)
    data_dir = Path(os.getenv("DATA_DIR", "var"))
    db_path = Path(os.getenv("DB_PATH", str(data_dir / "o365pop.sqlite3")))
    settings = Settings(
        azure_client_id=os.getenv("AZURE_CLIENT_ID", ""),
        azure_tenant_id=os.getenv("AZURE_TENANT_ID", "common"),
        token_encryption_key=os.getenv("TOKEN_ENCRYPTION_KEY", ""),
        mailbox_user=os.getenv("MAILBOX_USER", ""),
        mailbox_password=os.getenv("MAILBOX_PASSWORD", ""),
        pop3_bind=os.getenv("POP3_BIND", "127.0.0.1"),
        pop3_port=_env_int("POP3_PORT", 110),
        smtp_bind=os.getenv("SMTP_BIND", "127.0.0.1"),
        smtp_port=_env_int("SMTP_PORT", 587),
        allow_lan=os.getenv("ALLOW_LAN", "0") in ("1", "true", "TRUE"),
        celery_broker_url=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        celery_result_backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
        graph_poll_seconds=_env_int("GRAPH_POLL_SECONDS", 120),
        spool_scan_seconds=_env_int("SPOOL_SCAN_SECONDS", 30),
        task_snapshot_seconds=_env_int("TASK_SNAPSHOT_SECONDS", 60),
        task_snapshot_path=Path(os.getenv("TASK_SNAPSHOT_PATH") or str(data_dir / "tasks" / "snapshot.json")),
        cal_snapshot_seconds=_env_int("CAL_SNAPSHOT_SECONDS", 60),
        cal_snapshot_path=Path(os.getenv("CAL_SNAPSHOT_PATH") or str(data_dir / "calendar" / "snapshot.json")),
        cal_window_past_days=_env_int("CAL_WINDOW_PAST_DAYS", 30),
        cal_window_future_days=_env_int("CAL_WINDOW_FUTURE_DAYS", 180),
        data_dir=data_dir,
        db_path=db_path,
        log_dir=Path(os.getenv("LOG_DIR", "logs")),
    )
    logger.info(
        "config.load_settings | exit | data_dir=%s db_path=%s log_dir=%s pop3=%s:%s",
        settings.data_dir,
        settings.db_path,
        settings.log_dir,
        settings.pop3_bind,
        settings.pop3_port,
    )
    return settings


def _env_int(name: str, default: int) -> int:
    """Parse an integer environment variable.

    :param name: Variable name. Example: ``"POP3_PORT"``
    :param default: Fallback. Example: ``110``
    :return: Parsed int. Example: ``110``
    :raises ValueError: if the value is present but not an integer
    """
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


_UNSPECIFIED_BINDS = frozenset({"0.0.0.0", "::"})


def validate_bind(bind: str, *, allow_lan: bool) -> None:
    """Reject unspecified WAN binds unless ALLOW_LAN is set (DEP1.1).

    :param bind: Listen address. Example: ``"10.8.0.1"``
    :param allow_lan: When True, ``0.0.0.0`` is allowed. Example: ``False``
    :return: None
    :raises ValueError: if bind is empty or ``0.0.0.0`` without allow_lan
    """
    logger.info("config.validate_bind | entry | bind=%s allow_lan=%s", bind, allow_lan)
    try:
        _assert_bind_allowed(bind, allow_lan=allow_lan)
    except ValueError as exc:
        logger.error(
            "config.validate_bind | error | bind=%s allow_lan=%s err=%s",
            bind,
            allow_lan,
            exc,
        )
        raise
    logger.info("config.validate_bind | config | bind=%s allow_lan=%s", bind, allow_lan)
    logger.info("config.validate_bind | exit | status=ok bind=%s", bind)


def _assert_bind_allowed(bind: str, *, allow_lan: bool) -> None:
    """Raise if bind is empty or an unspecified WAN address without allow_lan.

    :param bind: Listen address. Example: ``"10.8.0.1"``
    :param allow_lan: When True, ``0.0.0.0`` / ``::`` are allowed. Example: ``False``
    :return: None
    :raises ValueError: if bind is empty or unspecified without allow_lan
    """
    address = (bind or "").strip()
    if not address:
        raise ValueError("bind address is required")
    if address in _UNSPECIFIED_BINDS and not allow_lan:
        raise ValueError(f"unspecified bind {address!r} requires ALLOW_LAN=1")
