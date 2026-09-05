"""POP1.3 — DELE local only."""

from __future__ import annotations

import poplib
from pathlib import Path

import pytest

from o365pop.db import connect
from o365pop.mailstore.maildir import MaildirStore
from o365pop.tosser.index import TossedMessage, record_tossed
from tests.integration.test_pop_retrieve import POP_HOST, seed_local_mailbox, start_popd, stop_popd
from tests.support.mailbox import MailboxSandbox

POP_DELE_PORT = 11112


@pytest.mark.integration
def test_pop_dele_removes_maildir_keeps_tossed_message(sandbox: MailboxSandbox) -> None:
    """TossedMessage remains; Graph unused.

    :return: None
    """
    seed_local_mailbox(sandbox)
    conn = connect(sandbox.db_path)
    record_tossed(
        conn,
        TossedMessage(
            graph_id="AAMk-outlook-1",
            source="outlook",
            message_id="<outlook.AAMk-outlook-1@o365pop.local>",
            chat_id=None,
            uidl="uid-outlook-1",
        ),
    )
    conn.close()

    proc = start_popd(sandbox, POP_DELE_PORT)
    try:
        client = poplib.POP3(POP_HOST, POP_DELE_PORT, timeout=5)
        client.user("denis")
        client.pass_("local-pass")
        assert client.dele(1).startswith(b"+OK")
        client.quit()
    finally:
        stop_popd(proc)

    assert MaildirStore(sandbox.maildir).list_uidls() == []
    conn = connect(sandbox.db_path)
    row = conn.execute("SELECT graph_id FROM tossed_message WHERE graph_id = ?", ("AAMk-outlook-1",)).fetchone()
    conn.close()
    assert row is not None
    assert "from o365pop.graph" not in Path("o365pop/popd/mailbox.py").read_text(encoding="utf-8")
    assert "from o365pop.graph" not in Path("o365pop/popd/service.py").read_text(encoding="utf-8")
