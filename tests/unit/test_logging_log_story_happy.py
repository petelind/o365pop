"""TFK-02 golden — ``assert_log_story`` keyword contract."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from o365pop.logging_setup import configure_logging
from tests.support.log_story import assert_log_story


@pytest.mark.unit
@pytest.mark.log_story
def test_configure_logging_log_story_happy(
    tmp_log_dir: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Happy path: entry and exit beats with required fragments.

    :param tmp_log_dir: Isolated logs directory. Example: ``Path("/tmp/.../logs")``
    :param caplog: pytest log capture
    :return: None
    """
    configure_logging(tmp_log_dir)
    app_logger = logging.getLogger("o365pop")
    app_logger.addHandler(caplog.handler)
    caplog.handler.setLevel("INFO")
    app_logger.info("HealthCheck.run | entry | probe=bootstrap")
    app_logger.info("HealthCheck.run | exit | status=ok")
    assert_log_story(
        caplog,
        where="HealthCheck.run",
        beats={"entry": ["probe=bootstrap"], "exit": ["status=ok"]},
    )


@pytest.mark.unit
@pytest.mark.log_story
def test_assert_log_story_rejects_missing_beat(caplog: pytest.LogCaptureFixture) -> None:
    """Missing beat fails with the beat name in the message.

    :param caplog: pytest log capture
    :return: None
    """
    app_logger = logging.getLogger("o365pop")
    app_logger.addHandler(caplog.handler)
    caplog.handler.setLevel("INFO")
    app_logger.info("HealthCheck.run | entry | probe=bootstrap")
    with pytest.raises(AssertionError, match="beat='exit'"):
        assert_log_story(
            caplog,
            where="HealthCheck.run",
            beats={"entry": ["probe=bootstrap"], "exit": ["status=ok"]},
        )
