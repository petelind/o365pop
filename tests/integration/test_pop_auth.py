"""POP1.2 — wrong password."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_pop_wrong_password_is_rejected_without_logging_secret(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """-ERR; password absent from logs.

    :param caplog: pytest log capture.
    :return: None
    """
    raise NotImplementedError()
