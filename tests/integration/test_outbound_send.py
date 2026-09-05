"""SEND1.1 — scanner POST MIME sendMail."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_scan_outbound_posts_same_mime_and_moves_to_sent() -> None:
    """FileGraphAdapter records MIME; file in spool/sent.

    :return: None
    """
    raise NotImplementedError()
