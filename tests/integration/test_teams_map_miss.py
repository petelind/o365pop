"""TEAM1.4 — unknown o365pop.local fail-closed."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_scan_unknown_teams_address_does_not_call_graph() -> None:
    """map_miss → failed; Graph unused.

    :return: None
    """
    raise NotImplementedError()
