"""AUTH1.1 — device-code login via DeviceCodePort fixture (no live Microsoft)."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_login_device_code_with_fixture_stores_encrypted_tokens(caplog: pytest.LogCaptureFixture) -> None:
    """Persists encrypted tokens for denis@example.com and logs exit without secrets.

    :param caplog: pytest log capture. Example: test ``caplog``
    :return: None
    """
    raise NotImplementedError()
