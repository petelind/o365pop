"""TEAM1.1 — In-Reply-To → chat post."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_scan_in_reply_to_posts_chat_not_send_mail() -> None:
    """POST chat; no sendMail; route=teams_chat.

    :return: None
    """
    raise NotImplementedError()
