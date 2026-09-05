"""SYNC1.2 — chat id ↔ teams.* local-part."""

from __future__ import annotations

import pytest

from o365pop.tosser.chat_address import decode_chat_b32, encode_chat_id, parse_reply_address, reply_address


@pytest.mark.unit
def test_encode_decode_roundtrip_thread_v2_id() -> None:
    """19:general@thread.v2 survives encode/decode.

    :return: None
    """
    chat_id = "19:general@thread.v2"
    token = encode_chat_id(chat_id)
    assert token.islower()
    assert "=" not in token
    assert decode_chat_b32(token) == chat_id
    address = reply_address(chat_id)
    assert address.startswith("teams.")
    assert address.endswith("@o365pop.local")
    assert parse_reply_address(address) == token
