"""Unit — live journey env gate (no Microsoft)."""

from __future__ import annotations

import pytest

from tests.support.live_session import build_probe_rfc822, live_env_skip_reason


@pytest.mark.unit
def test_live_env_skip_reason_when_azure_client_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """AZURE_CLIENT_ID empty → skip reason names the var.

    :return: None
    """
    monkeypatch.setenv("AZURE_CLIENT_ID", "")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "test-key")
    monkeypatch.setenv("MAILBOX_USER", "denis")
    monkeypatch.setenv("MAILBOX_PASSWORD", "local-only")
    reason = live_env_skip_reason()
    assert reason is not None
    assert "AZURE_CLIENT_ID" in reason


@pytest.mark.unit
def test_live_env_skip_reason_none_when_required_vars_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """Required live vars present → no skip.

    :return: None
    """
    monkeypatch.setenv("AZURE_CLIENT_ID", "11111111-2222-3333-4444-555555555555")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "test-fernet-key")
    monkeypatch.setenv("MAILBOX_USER", "denis")
    monkeypatch.setenv("MAILBOX_PASSWORD", "local-only")
    assert live_env_skip_reason() is None


@pytest.mark.unit
def test_build_probe_rfc822_includes_subject_not_password() -> None:
    """Probe MIME has the subject and a short body.

    :return: None
    """
    raw = build_probe_rfc822(
        subject="o365pop-live-abcd",
        from_addr="denis@example.com",
        to_addr="denis@example.com",
        body="probe",
    )
    assert b"Subject: o365pop-live-abcd" in raw
    assert b"probe" in raw
