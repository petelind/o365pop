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
    assert message.get_content_type() == "text/plain"
    assert "Ship it" in message.get_content()


@pytest.mark.unit
def test_teams_to_rfc822_html_body_is_multipart_alternative() -> None:
    """Graph HTML becomes text/html plus a tag-free text/plain part.

    :return: None
    """
    html = (
        "<p>Thank you for amazing words!</p>"
        "<p>&nbsp;</p>"
        "<p>A question: some contractors are awaiting contract extensions.</p>"
    )
    message = teams_to_rfc822(
        chat_id="19:general",
        graph_message_id="teams-msg-html-1",
        from_name="Ada Lovelace",
        body=html,
        chat_subject="general",
        body_content_type="html",
    )
    assert message.get_content_type() == "multipart/alternative"
    plain = message.get_body(preferencelist=("plain",))
    rich = message.get_body(preferencelist=("html",))
    assert plain is not None
    assert rich is not None
    plain_text = plain.get_content()
    rich_text = rich.get_content()
    assert "Thank you for amazing words!" in plain_text
    assert "<p>" not in plain_text
    assert "&nbsp;" not in plain_text
    assert "<p>Thank you for amazing words!</p>" in rich_text
    assert "text/html" in rich.get_content_type()
