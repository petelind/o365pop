"""TEAM — strip quoted history."""

from __future__ import annotations

import pytest

from o365pop.tosser.reply_text import extract


@pytest.mark.unit
def test_extract_keeps_text_before_original_message_marker() -> None:
    """On it above -----Original Message----- remains.

    :return: None
    """
    body = "On it\n\n-----Original Message-----\nFrom: Ada Lovelace\nShip it\n"
    assert extract(body) == "On it"
    assert extract("On it\n\n> Ship it") == "On it"
    assert extract("On it\n\nFrom: Ada Lovelace <teams.mjqxg2a@o365pop.local>\n") == "On it"
