"""BOOT1.2 — rotating ``logs/app.log`` and log-story helper."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from o365pop.logging_setup import configure_logging
from tests.support.log_story import assert_log_story


@pytest.mark.unit
def test_configure_logging_writes_info_with_beat(tmp_log_dir: Path, caplog: pytest.LogCaptureFixture) -> None:
    """INFO lines land in app.log and include a beat token.

    :param tmp_log_dir: Isolated logs directory. Example: ``Path("/tmp/.../logs")``
    :param caplog: pytest log capture
    :return: None
    """
    log_path = configure_logging(tmp_log_dir)
    app_logger = logging.getLogger("o365pop")
    app_logger.addHandler(caplog.handler)
    caplog.handler.setLevel("INFO")
    app_logger.info("HealthCheck.run | entry | probe=bootstrap")
    app_logger.info("HealthCheck.run | exit | status=ok")
    text = log_path.read_text(encoding="utf-8")
    assert "| entry |" in text
    assert "| exit |" in text
    assert "HealthCheck.run" in text
    assert_log_story(
        caplog,
        [
            {"where": "HealthCheck.run", "beat": "entry", "must_include": ["probe=bootstrap"]},
            {"where": "HealthCheck.run", "beat": "exit", "must_include": ["status=ok"]},
        ],
    )


@pytest.mark.unit
def test_configure_logging_rotates_existing_file_on_start(tmp_log_dir: Path) -> None:
    """A non-empty app.log from a prior process is rotated on configure.

    :param tmp_log_dir: Isolated logs directory. Example: ``Path("/tmp/.../logs")``
    :return: None
    """
    prior = tmp_log_dir / "app.log"
    prior.write_text("prior-process-line\n", encoding="utf-8")
    log_path = configure_logging(tmp_log_dir)
    backup = tmp_log_dir / "app.log.1"
    assert backup.is_file()
    assert "prior-process-line" in backup.read_text(encoding="utf-8")
    assert "prior-process-line" not in log_path.read_text(encoding="utf-8")
