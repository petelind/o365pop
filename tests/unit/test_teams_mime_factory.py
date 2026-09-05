"""SYNC1.2 — From/Reply-To are teams.*; Message-ID minted."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_teams_to_rfc822_from_is_teams_address_not_real_smtp() -> None:
    """From must be teams.*@o365pop.local, not ada@example.com.

    :return: None
    """
    raise NotImplementedError()
