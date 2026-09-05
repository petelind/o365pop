"""SYNC — HttpGraphAdapter URL construction (unit; MockTransport allowed)."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_list_inbox_messages_uses_inbox_messages_path() -> None:
    """GET path is /me/mailFolders/inbox/messages.

    :return: None
    """
    raise NotImplementedError()
