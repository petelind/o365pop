"""TEAM1.1–1.4 decision table."""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

import pytest

from o365pop.db import connect, init_schema
from o365pop.tosser.index import TossedMessage, record_tossed
from o365pop.tosser.outbound_router import OutboundRouter

TEAMS_MESSAGE_ID = "<teams.mjqxg2a.abc@o365pop.local>"


def _open_db(tmp_db_path: Path):
    """Schema-ready sqlite for router unit tests.

    :param tmp_db_path: Isolated db path. Example: ``Path("/tmp/.../o365pop.sqlite3")``
    :return: Connection. Example: ``<sqlite3.Connection>``
    """
    conn = connect(tmp_db_path)
    init_schema(conn)
    return conn


def _seed_teams_tossed(conn) -> None:
    """Insert the fixture Teams TossedMessage.

    :param conn: sqlite connection. Example: ``connect(path)``
    :return: None
    """
    record_tossed(
        conn,
        TossedMessage(
            graph_id="teams-msg-1",
            source="teams",
            message_id=TEAMS_MESSAGE_ID,
            chat_id="19:general",
            uidl="uid-teams-1",
        ),
    )


@pytest.mark.unit
def test_route_in_reply_to_teams_message_id_is_teams_chat(tmp_db_path: Path) -> None:
    """In-Reply-To matching TossedMessage → teams_chat.

    :return: None
    """
    conn = _open_db(tmp_db_path)
    _seed_teams_tossed(conn)
    message = EmailMessage()
    message["In-Reply-To"] = TEAMS_MESSAGE_ID
    message["To"] = "ada@example.com"
    message["Subject"] = "Re: Teams: general"
    message.set_content("On it")
    route = OutboundRouter(conn).route(message)
    conn.close()
    assert route.kind == "teams_chat"
    assert route.chat_id == "19:general"


@pytest.mark.unit
def test_route_unknown_o365pop_local_is_map_miss(tmp_db_path: Path) -> None:
    """teams.unknown@o365pop.local → map_miss.

    :return: None
    """
    conn = _open_db(tmp_db_path)
    message = EmailMessage()
    message["To"] = "teams.unknown@o365pop.local"
    message["Subject"] = "Orphan reply"
    message.set_content("hello")
    route = OutboundRouter(conn).route(message)
    conn.close()
    assert route.kind == "map_miss"
    assert route.chat_id is None
