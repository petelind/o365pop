"""Session-scoped captured Microsoft login for the operator journey."""

from __future__ import annotations

import pytest

from tests.support.live_session import LiveSession, ensure_captured_session, live_env_skip_reason


@pytest.fixture(scope="session")
def live_session() -> LiveSession:
    """One device-code capture per pytest process; reuse encrypted vault after that.

    :return: Captured session. Example: ``LiveSession(username="denis@contoso.com", ...)``
    """
    reason = live_env_skip_reason()
    if reason:
        pytest.skip(reason)
    return ensure_captured_session()
