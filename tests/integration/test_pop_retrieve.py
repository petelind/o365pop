"""POP1.1 — real poplib, no TLS."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_pop_stat_uidl_retr_top_without_tls() -> None:
    """USER/PASS STAT=1 UIDL RETR Subject TOP headers.

    :return: None
    """
    raise NotImplementedError()
