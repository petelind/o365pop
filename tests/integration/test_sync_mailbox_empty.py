"""SYNC1.3 — empty inbox/chats is completed tossed=0."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_sync_mailbox_with_empty_graph_completes_zero_tossed() -> None:
    """status=completed tossed=0.

    :return: None
    """
    raise NotImplementedError()
