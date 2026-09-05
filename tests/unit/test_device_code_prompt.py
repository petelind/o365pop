"""AUTH — device-code prompt is visible on stderr (no secrets)."""

from __future__ import annotations

import pytest

from o365pop.accounts.errors import AuthenticationError
from o365pop.accounts.graph_auth import _bundle_from_msal, emit_device_code_prompt


@pytest.mark.unit
def test_emit_device_code_prompt_writes_url_and_code(capsys: pytest.CaptureFixture[str]) -> None:
    """stderr has the verification URL and user code.

    :return: None
    """
    emit_device_code_prompt(
        {
            "user_code": "ABCD1234",
            "verification_uri": "https://www.microsoft.com/link",
        }
    )
    captured = capsys.readouterr()
    assert "https://www.microsoft.com/link" in captured.err
    assert "ABCD1234" in captured.err
    assert captured.err.count("ABCD1234") == 1


@pytest.mark.unit
def test_emit_device_code_prompt_missing_code_raises() -> None:
    """Empty flow fails closed.

    :return: None
    """
    with pytest.raises(AuthenticationError, match="device_code_rejected"):
        emit_device_code_prompt({})


@pytest.mark.unit
def test_bundle_from_msal_device_flow_expired_is_device_code_rejected() -> None:
    """Expired device code is not labeled as refresh failure.

    :return: None
    """
    with pytest.raises(AuthenticationError, match="device_code_rejected"):
        _bundle_from_msal({"error": "expired_token"}, flow="device_code")
