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
    app.conf.update(
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_soft_time_limit=SOFT_TIME_LIMIT_SECONDS,
        task_time_limit=HARD_TIME_LIMIT_SECONDS,
        task_always_eager=_env_flag("CELERY_TASK_ALWAYS_EAGER"),
    )
    logger.info(
        "celery_app.create_celery_app | exit | name=%s acks_late=%s prefetch=%s",
        app.main,
        app.conf.task_acks_late,
        app.conf.worker_prefetch_multiplier,
    )
    return app


def _env_flag(name: str) -> bool:
    """True when an env var is a truthy flag.

    :param name: Variable name. Example: ``"CELERY_TASK_ALWAYS_EAGER"``
    :return: Parsed flag. Example: ``False``
    """
    return os.getenv(name, "").lower() in ("1", "true", "yes")


celery_app = create_celery_app()
