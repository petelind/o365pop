"""BOOT1.3 — Celery app name and taciturn2-style worker flags."""

from __future__ import annotations

import pytest

from o365pop.celery_app import create_celery_app


@pytest.mark.unit
def test_celery_app_name_and_acks_late() -> None:
    """App is named o365pop with acks_late and prefetch=1.

    :return: None
    """
    app = create_celery_app(broker_url="memory://", result_backend="cache+memory://")
    assert app.main == "o365pop"
    assert app.conf.task_acks_late is True
    assert app.conf.worker_prefetch_multiplier == 1


@pytest.mark.unit
def test_module_level_celery_app_matches_name() -> None:
    """Importing ``celery_app`` yields the same configured name.

    :return: None
    """
    from o365pop.celery_app import celery_app

    assert celery_app.main == "o365pop"
    assert celery_app.conf.task_acks_late is True


@pytest.mark.unit
def test_celery_beat_includes_scan_outbound_spool() -> None:
    """Beat runs scan_outbound_spool every SPOOL_SCAN_SECONDS.

    :return: None
    """
    app = create_celery_app(broker_url="memory://", result_backend="cache+memory://")
    entry = app.conf.beat_schedule["scan-outbound-spool"]
    assert entry["task"] == "o365pop.sync.scan_outbound_spool"
    assert entry["schedule"] == 30.0
