"""SYNC1.1 — Outlook MIME toss + dedup."""

from __future__ import annotations

import logging

import pytest

from o365pop.graph.file_adapter import FileGraphAdapter
from o365pop.mailstore.maildir import MaildirStore
from o365pop.tosser.inbound import InboundTosser, subject_of
from tests.support.fixtures import load_graph_case
from tests.support.log_story import assert_log_story
from tests.support.mailbox import open_sandbox_db


@pytest.mark.integration
@pytest.mark.log_story
def test_toss_outlook_writes_one_maildir_message_and_skips_duplicate(sandbox, caplog: pytest.LogCaptureFixture) -> None:
    """Subject Q3 close; second toss skipped_dup=1.

    :return: None
    """
    caplog.set_level(logging.INFO)
    conn = open_sandbox_db(sandbox)
    store = MaildirStore(sandbox.maildir)
    tosser = InboundTosser(conn, store, FileGraphAdapter(load_graph_case("SYNC1.1-outlook-q3-close")))
    first = tosser.toss_all()
    assert first == {"tossed": 1, "skipped_dup": 0}
    assert len(store.list_uidls()) == 1
    uidl, _size = store.list_uidls()[0]
    assert subject_of(store.get(uidl)) == "Q3 close"
    row = conn.execute("SELECT graph_id, source FROM tossed_message").fetchone()
    assert row["graph_id"] == "AAMk-outlook-1"
    assert row["source"] == "outlook"
    second = tosser.toss_all()
    assert second["skipped_dup"] == 1
    assert second["tossed"] == 0
    assert len(store.list_uidls()) == 1
    assert_log_story(
        caplog,
        where="InboundTosser.toss_all",
        beats={"processing": ["tossed=1", "skipped_dup=0"]},
    )
    conn.close()
