"""SYNC1.2 — Teams RFC822 + ChatMap."""

from __future__ import annotations

import email

import pytest

from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.mailstore.maildir import MaildirStore
from o365pop.tosser.chat_address import reply_address
from o365pop.tosser.inbound import InboundTosser
from tests.support.fixtures import load_graph_case
from tests.support.mailbox import open_sandbox_db


@pytest.mark.integration
def test_toss_teams_mints_reply_map_and_chat_map(sandbox) -> None:
    """From teams.*; Message-ID <teams.; ChatMap for 19:general.

    :return: None
    """
    conn = open_sandbox_db(sandbox)
    store = MaildirStore(sandbox.maildir)
    tosser = InboundTosser(conn, store, FileGraphAdapter(load_graph_case("SYNC1.2-teams-ship-it")))
    result = tosser.toss_all()
    assert result["tossed"] == 1
    uidl, _size = store.list_uidls()[0]
    parsed = email.message_from_bytes(store.get(uidl))
    address = reply_address("19:general")
    assert parsed["Subject"].startswith("Teams:")
    assert "Ada Lovelace" in parsed["From"]
    assert address in parsed["From"]
    assert "ada@" not in parsed["From"].lower()
    assert parsed["Reply-To"] == address
    assert parsed["Message-ID"].startswith("<teams.")
    assert "Ship it" in parsed.get_payload()
    tossed = conn.execute("SELECT source, message_id, chat_id FROM tossed_message").fetchone()
    assert tossed["source"] == "teams"
    assert tossed["message_id"] == parsed["Message-ID"]
    mapped = conn.execute("SELECT reply_address FROM chat_map WHERE chat_id = ?", ("19:general",)).fetchone()
    assert mapped["reply_address"] == address
    conn.close()
