"""AUTH1.2 — refresh expired access token."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_refresh_access_token_with_expired_access_stores_new_expiry() -> None:
    """Expired access + valid refresh stores a future expiry.

    :return: None
    """
    raise NotImplementedError()


@pytest.mark.unit
def test_refresh_access_token_with_revoked_refresh_raises_authentication_error() -> None:
    """Rejected refresh raises AuthenticationError.

    :return: None
    """
    raise NotImplementedError()
