"""DEP1.1 — WireGuard bind policy."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_validate_bind_rejects_unspecified_without_allow_lan() -> None:
    """0.0.0.0 with allow_lan=False raises ValueError.

    :return: None
    """
    raise NotImplementedError()


@pytest.mark.unit
def test_validate_bind_accepts_wireguard_address() -> None:
    """10.8.0.1 is accepted.

    :return: None
    """
    raise NotImplementedError()
