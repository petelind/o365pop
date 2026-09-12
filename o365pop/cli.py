"""Operator CLI: ``python -m o365pop <command>``."""

from __future__ import annotations

import argparse
import logging
import platform
import shutil
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path

from o365pop import __version__
from o365pop.accounts.errors import AuthenticationError
from o365pop.accounts.graph_auth import (
    GraphAuthService,
    live_device_code_port,
    live_interactive_port,
    live_msal_port,
)
from o365pop.accounts.ports import DeviceCodePort
from o365pop.accounts.store import _hash_local_password, get_account, upsert_account
from o365pop.config import Settings, load_settings
from o365pop.db import REQUIRED_TABLES, connect, init_schema, list_tables
from o365pop.logging_setup import configure_logging

logger = logging.getLogger(__name__)

_STUB_FEATURES: dict[str, str] = {}


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch a CLI command.

    :param argv: Arguments without the program name. Example: ``["status"]``
    :return: Process exit code. Example: ``0``
    :raises SystemExit: not used — callers receive an int
    """
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    settings = load_settings()
    configure_logging(settings.log_dir)
    logger.info("cli.main | entry | command=%s", args.command)
    if args.command == "status":
        return run_status(settings)
    if args.command == "init-db":
        return run_init_db(settings)
    if args.command == "login":
        return run_login(settings, interactive=args.interactive)
    if args.command == "popd":
        return run_popd(settings)
    if args.command == "smtpd":
        return run_smtpd(settings)
    return run_stub(args.command)


def run_status(settings: Settings) -> int:
    """Print a health dashboard to stdout (BSP-07, no HTTP UI).

    :param settings: Loaded settings. Example: ``load_settings()``
    :return: ``0`` if required checks pass, ``1`` otherwise. Example: ``0``
    """
    logger.info("cli.run_status | entry | db_path=%s", settings.db_path)
    checks = _collect_health_checks(settings)
    failed = [check for check in checks if check["status"] != "ok"]
    print(f"o365pop {__version__} — {'healthy' if not failed else 'degraded'}")
    print(f"Python {sys.version.split()[0]} · {platform.platform()}")
    for check in checks:
        mark = "✅" if check["status"] == "ok" else "❌"
        print(f"  {mark} {check['name']}: {check['detail']}")
    logger.info(
        "cli.run_status | exit | status=%s failed=%s",
        "ok" if not failed else "degraded",
        [check["name"] for check in failed],
    )
    return 0 if not failed else 1


def run_init_db(settings: Settings) -> int:
    """Create the SQLite file and apply ``schema.sql``.

    :param settings: Loaded settings. Example: ``load_settings()``
    :return: ``0`` on success. Example: ``0``
    """
    logger.info("cli.run_init_db | entry | db_path=%s", settings.db_path)
    conn = connect(settings.db_path)
    try:
        init_schema(conn)
        tables = list_tables(conn)
    finally:
        conn.close()
    print(f"Schema ready at {settings.db_path} tables={tables}")
    logger.info("cli.run_init_db | exit | tables=%s", tables)
    return 0


def run_login(settings: Settings, *, interactive: bool = False) -> int:
    """Microsoft login; store encrypted tokens (AUTH).

    :param settings: Loaded settings. Example: ``load_settings()``
    :param interactive: Loopback PKCE when True. Example: ``True``
    :return: ``0`` on success, ``1`` on auth/config failure. Example: ``0``
    """
    logger.info("cli.run_login | entry | interactive=%s", interactive)
    if not settings.token_encryption_key:
        logger.error("cli.run_login | error | reason=missing_encryption_key")
        print("TOKEN_ENCRYPTION_KEY is required.", file=sys.stderr)
        return 1
    login_port = _login_port(settings, interactive=interactive)
    conn = connect(settings.db_path)
    try:
        init_schema(conn)
        _apply_local_mailbox(conn, settings)
        service = GraphAuthService(
            conn,
            settings.token_encryption_key,
            login_port,
            live_msal_port(settings.azure_client_id, settings.azure_tenant_id),
        )
        username = service.login_device_code()
    except (AuthenticationError, ValueError) as exc:
        logger.error("cli.run_login | error | reason=auth_failed")
        print(f"Login failed: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    _seed_live_e2e_vault(settings)
    print(f"Logged in as {username}")
    logger.info("cli.run_login | exit | user=%s", username)
    return 0


def _login_port(settings: Settings, *, interactive: bool) -> DeviceCodePort:
    """Pick device-code or loopback PKCE.

    :param settings: Loaded settings. Example: ``load_settings()``
    :param interactive: Loopback when True. Example: ``True``
    :return: DeviceCodePort. Example: ``live_interactive_port(...)``
    """
    if interactive:
        logger.info("cli._login_port | branch | flow=interactive")
        return live_interactive_port(settings.azure_client_id, settings.azure_tenant_id)
    logger.info("cli._login_port | branch | flow=device_code")
    return live_device_code_port(settings.azure_client_id, settings.azure_tenant_id)


def _seed_live_e2e_vault(settings: Settings) -> None:
    """Copy the operator vault so ``make test-e2e`` can reuse tokens.

    :param settings: Loaded settings. Example: ``load_settings()``
    :return: None
    """
    dest_dir = Path("var/live-e2e")
    dest = dest_dir / "o365pop.sqlite3"
    if not settings.db_path.is_file():
        return
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(settings.db_path, dest)
    logger.info("cli._seed_live_e2e_vault | exit | dest=%s", dest)


def run_popd(settings: Settings) -> int:
    """Start the Twisted POP3 daemon (cleartext USER/PASS).

    :param settings: Loaded settings. Example: ``load_settings()``
    :return: ``0`` after the reactor stops. Example: ``0``
    """
    from o365pop.popd.service import run_popd as serve_popd

    logger.info("cli.run_popd | entry | bind=%s port=%s", settings.pop3_bind, settings.pop3_port)
    serve_popd(
        bind=settings.pop3_bind,
        port=settings.pop3_port,
        maildir=settings.data_dir / "maildir",
        db_path=settings.db_path,
    )
    logger.info("cli.run_popd | exit | status=stopped")
    return 0


def run_smtpd(settings: Settings) -> int:
    """Start the aiosmtpd daemon (cleartext AUTH LOGIN).

    :param settings: Loaded settings. Example: ``load_settings()``
    :return: ``0`` after the server stops. Example: ``0``
    """
    from o365pop.smtpd.service import run_smtpd as serve_smtpd

    logger.info("cli.run_smtpd | entry | bind=%s port=%s", settings.smtp_bind, settings.smtp_port)
    serve_smtpd(
        bind=settings.smtp_bind,
        port=settings.smtp_port,
        spool_root=settings.data_dir / "spool",
        db_path=settings.db_path,
    )
    logger.info("cli.run_smtpd | exit | status=stopped")
    return 0


def _apply_local_mailbox(conn: sqlite3.Connection, settings: Settings) -> None:
    """Persist local POP/SMTP user without touching Graph tokens.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param settings: Loaded settings. Example: ``load_settings()``
    :return: None
    """
    if not settings.mailbox_user:
        return
    existing = get_account(conn)
    upsert_account(
        conn,
        display_name=existing.display_name if existing and existing.display_name else settings.mailbox_user,
        graph_user_id=existing.graph_user_id if existing and existing.graph_user_id else "",
        mailbox_user=settings.mailbox_user,
        mailbox_password_hash=_hash_local_password(settings.mailbox_password) if settings.mailbox_password else "",
    )


def run_stub(command: str) -> int:
    """Refuse a command that belongs to a later feature.

    :param command: CLI verb. Example: ``"login"``
    :return: ``2``. Example: ``2``
    """
    feature = _STUB_FEATURES.get(command, "a later feature")
    logger.warning("cli.run_stub | branch | command=%s feature=%s", command, feature)
    print(f"'{command}' is not implemented yet — see {feature}.", file=sys.stderr)
    return 2


def _collect_health_checks(settings: Settings) -> list[dict[str, str]]:
    """Run bootstrap health checks.

    :param settings: Loaded settings. Example: ``load_settings()``
    :return: Check dicts with name/status/detail. Example: ``[{"name": "Logging", ...}]``
    """
    checks: list[dict[str, str]] = [
        {
            "name": "Python",
            "status": "ok" if sys.version_info >= (3, 12) else "fail",
            "detail": sys.version.split()[0],
        },
        {
            "name": "Logging",
            "status": "ok" if settings.log_dir.is_dir() else "fail",
            "detail": str(settings.log_dir / "app.log"),
        },
    ]
    checks.append(_sqlite_check(settings))
    checks.append(_celery_check())
    return checks


def _sqlite_check(settings: Settings) -> dict[str, str]:
    """Verify schema tables exist (creates them if the file is new).

    :param settings: Loaded settings. Example: ``load_settings()``
    :return: One check row. Example: ``{"name": "SQLite", "status": "ok", ...}``
    """
    try:
        conn = connect(settings.db_path)
        try:
            init_schema(conn)
            tables = list_tables(conn)
        finally:
            conn.close()
    except Exception as exc:
        logger.error("cli._sqlite_check | error | err=%s", exc)
        return {"name": "SQLite", "status": "fail", "detail": str(exc)}
    missing = [name for name in REQUIRED_TABLES if name not in tables]
    if missing:
        return {"name": "SQLite", "status": "fail", "detail": f"missing {missing}"}
    return {"name": "SQLite", "status": "ok", "detail": ",".join(tables)}


def _celery_check() -> dict[str, str]:
    """Verify the Celery app name and acks_late (does not contact Redis).

    :return: One check row. Example: ``{"name": "Celery", "status": "ok", ...}``
    """
    from o365pop.celery_app import celery_app

    if celery_app.main == "o365pop" and celery_app.conf.task_acks_late:
        return {"name": "Celery", "status": "ok", "detail": "o365pop acks_late=true"}
    return {
        "name": "Celery",
        "status": "fail",
        "detail": f"name={celery_app.main} acks_late={celery_app.conf.task_acks_late}",
    }


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser.

    :return: Parser with subcommands. Example: ``ArgumentParser(prog="o365pop")``
    """
    parser = argparse.ArgumentParser(prog="o365pop", description="o365pop operator CLI")
    parser.add_argument(
        "command",
        choices=("status", "init-db", "login", "popd", "smtpd"),
        help="status|init-db now; login/popd/smtpd later",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="login via loopback PKCE (browser). Needed on work tenants.",
    )
    return parser
