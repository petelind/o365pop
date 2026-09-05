"""SYNC1.2 — From/Reply-To are teams.*; Message-ID minted."""

from __future__ import annotations

import pytest

from o365pop.tosser.chat_address import reply_address
from o365pop.tosser.mime_factory import teams_to_rfc822


@pytest.mark.unit
def test_teams_to_rfc822_from_is_teams_address_not_real_smtp() -> None:
    """From must be teams.*@o365pop.local, not ada@example.com.

    :return: None
    """
    message = teams_to_rfc822(
        chat_id="19:general",
        graph_message_id="teams-msg-1",
        from_name="Ada Lovelace",
        body="Ship it",
        chat_subject="general",
    )
    address = reply_address("19:general")
    assert address in message["From"]
    assert "ada@" not in message["From"].lower()
    assert message["Reply-To"] == address
    assert str(message["Message-ID"]).startswith("<teams.")
    assert message["X-O365POP-Source"] == "teams"
