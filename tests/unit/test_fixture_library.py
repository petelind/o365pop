"""TFK-04 — fixture catalog files load and sandbox applies presets."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.fixtures import load_graph_case, load_graph_json, load_mail, load_preset
from tests.support.mailbox import apply_preset, mailbox_sandbox, open_sandbox_db


@pytest.mark.unit
def test_load_graph_case_outlook_q3_close() -> None:
    """SYNC1.1 inbox lists AAMk-outlook-1 with subject Q3 close.

    :return: None
    """
    inbox = load_graph_json("SYNC1.1-outlook-q3-close", "inbox.json")
    assert inbox["value"][0]["id"] == "AAMk-outlook-1"
    assert inbox["value"][0]["subject"] == "Q3 close"
    mime = (load_graph_case("SYNC1.1-outlook-q3-close") / "message.eml").read_bytes()
    assert b"Subject: Q3 close" in mime


@pytest.mark.unit
def test_load_graph_case_empty() -> None:
    """SYNC1.3 cases have empty value lists.

    :return: None
    """
    assert load_graph_json("SYNC1.3-empty", "inbox.json")["value"] == []
    assert load_graph_json("SYNC1.3-empty", "chats.json")["value"] == []


@pytest.mark.unit
def test_load_mail_contains_subject() -> None:
    """RFC822 fixtures include the catalog subjects.

    :return: None
    """
    assert b"Subject: Hello Ada" in load_mail("hello-ada")
    assert b"X-O365POP-Source: teams" in load_mail("teams-ship-it")


@pytest.mark.unit
def test_authenticated_preset_seeds_mailbox(tmp_path: Path) -> None:
    """authenticated_mailbox preset inserts the single v1 account row.

    :param tmp_path: Isolated workspace. Example: ``Path("/tmp/pytest-...")``
    :return: None
    """
    sandbox = mailbox_sandbox(tmp_path / "sandbox")
    conn = open_sandbox_db(sandbox)
    try:
        apply_preset(conn, "authenticated_mailbox")
        row = conn.execute("SELECT mailbox_user FROM mailbox_account WHERE id = 1").fetchone()
        assert row["mailbox_user"] == "denis"
        assert load_preset("empty")["mailbox_account"] == []
    finally:
        conn.close()


@pytest.mark.unit
def test_missing_graph_case_raises() -> None:
    """Unknown catalog id fails fast.

    :return: None
    """
    with pytest.raises(FileNotFoundError, match="graph case not found"):
        load_graph_json("NOT-A-CASE", "inbox.json")
