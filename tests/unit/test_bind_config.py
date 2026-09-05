"""DEP1.1 — WireGuard bind policy."""

from __future__ import annotations

import logging

import pytest

from o365pop.config import validate_bind
from tests.support.log_story import assert_log_story


@pytest.mark.unit
def test_validate_bind_rejects_unspecified_without_allow_lan() -> None:
    """0.0.0.0 with allow_lan=False raises ValueError.

    :return: None
    """
    with pytest.raises(ValueError):
        validate_bind("0.0.0.0", allow_lan=False)
    with pytest.raises(ValueError):
        validate_bind("::", allow_lan=False)
    with pytest.raises(ValueError):
        validate_bind("", allow_lan=False)


@pytest.mark.unit
def test_validate_bind_accepts_wireguard_address(caplog: pytest.LogCaptureFixture) -> None:
    """10.8.0.1 is accepted.

    :return: None
    """
    caplog.set_level(logging.INFO)
    validate_bind("10.8.0.1", allow_lan=False)
    validate_bind("127.0.0.1", allow_lan=False)
    assert_log_story(
        caplog,
        where="validate_bind",
        beats={"config": ["bind="]},
    )


@pytest.mark.unit
def test_validate_bind_accepts_unspecified_when_allow_lan() -> None:
    """0.0.0.0 with allow_lan=True is accepted.

    :return: None
    """
    validate_bind("0.0.0.0", allow_lan=True)
