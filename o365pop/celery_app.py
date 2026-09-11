"""Celery application without Django (taciturn2 process shape)."""

from __future__ import annotations

import logging
import os

from celery import Celery

logger = logging.getLogger(__name__)

SOFT_TIME_LIMIT_SECONDS = 600
HARD_TIME_LIMIT_SECONDS = 660


def create_celery_app(
    broker_url: str | None = None,
    result_backend: str | None = None,
) -> Celery:
    """Build the o365pop Celery app (acks_late, prefetch=1).

    :param broker_url: Redis broker. Example: ``"redis://localhost:6379/0"``
    :param result_backend: Result backend. Example: ``"redis://localhost:6379/0"``
    :return: Configured Celery app. Example: ``Celery("o365pop")``
    """
    broker = broker_url or os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    backend = result_backend or os.getenv("CELERY_RESULT_BACKEND", broker)
    logger.info("celery_app.create_celery_app | entry | broker_set=%s", bool(broker))
    app = Celery("o365pop", broker=broker, backend=backend)
    poll_seconds = _env_positive_int("GRAPH_POLL_SECONDS", 120)
    spool_seconds = _env_positive_int("SPOOL_SCAN_SECONDS", 30)
    task_seconds = _env_positive_int("TASK_SNAPSHOT_SECONDS", 60)
    cal_seconds = _env_positive_int("CAL_SNAPSHOT_SECONDS", 60)
    app.conf.update(
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_soft_time_limit=SOFT_TIME_LIMIT_SECONDS,
        task_time_limit=HARD_TIME_LIMIT_SECONDS,
        task_always_eager=_env_flag("CELERY_TASK_ALWAYS_EAGER"),
        beat_schedule={
            "sync-mailbox": {
                "task": "o365pop.sync.sync_mailbox",
                "schedule": float(poll_seconds),
            },
            "scan-outbound-spool": {
                "task": "o365pop.sync.scan_outbound_spool",
                "schedule": float(spool_seconds),
            },
            "sync-tasks": {
                "task": "o365pop.sync.sync_tasks",
                "schedule": float(task_seconds),
            },
            "sync-calendar": {
                "task": "o365pop.sync.sync_calendar",
                "schedule": float(cal_seconds),
            },
        },
    )
    logger.info(
        "celery_app.create_celery_app | exit | name=%s acks_late=%s prefetch=%s "
        "beat=sync-mailbox,scan-outbound-spool,sync-tasks,sync-calendar "
        "interval=%s spool_interval=%s task_interval=%s cal_interval=%s",
        app.main,
        app.conf.task_acks_late,
        app.conf.worker_prefetch_multiplier,
        poll_seconds,
        spool_seconds,
        task_seconds,
        cal_seconds,
    )
    return app


def _env_flag(name: str) -> bool:
    """True when an env var is a truthy flag.

    :param name: Variable name. Example: ``"CELERY_TASK_ALWAYS_EAGER"``
    :return: Parsed flag. Example: ``False``
    """
    return os.getenv(name, "").lower() in ("1", "true", "yes")


def _env_positive_int(name: str, default: int) -> int:
    """Parse a positive integer env var, else ``default``.

    :param name: Variable name. Example: ``"GRAPH_POLL_SECONDS"``
    :param default: Fallback. Example: ``120``
    :return: Parsed int. Example: ``120``
    """
    raw = os.getenv(name, "")
    try:
        value = int(raw) if raw else default
    except ValueError:
        logger.warning("celery_app._env_positive_int | branch | name=%s invalid default=%s", name, default)
        return default
    if value <= 0:
        logger.warning("celery_app._env_positive_int | branch | name=%s nonpositive default=%s", name, default)
        return default
    return value


celery_app = create_celery_app()

# Register tasks after the app exists (worker/beat: ``-A o365pop.celery_app:celery_app``).
import o365pop.sync.tasks as _sync_tasks  # noqa: E402,F401
