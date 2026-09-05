"""SEND1.2 — Graph 400 → retry then failed."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_scan_outbound_graph_400_retries_then_failed() -> None:
    """After retry limit file is in spool/failed.

    :return: None
    """
    raise NotImplementedError()
