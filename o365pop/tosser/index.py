"""TossedMessage and ChatMap sqlite helpers."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TossedMessage:
    """Dedup + reply-map row.

    :param graph_id: Graph id. Example: ``"AAMk-outlook-1"``
    :param source: outlook|teams. Example: ``"teams"``
    :param message_id: RFC822 Message-ID. Example: ``"<teams.mjqxg2a.abc@o365pop.local>"``
    :param chat_id: Chat id or None. Example: ``"19:general"``
    :param uidl: POP UIDL. Example: ``"uid-outlook-1"``
    """

    graph_id: str
    source: str
    message_id: str
    chat_id: str | None
    uidl: str


def already_tossed(conn: sqlite3.Connection, graph_id: str) -> bool:
    """Whether graph_id is in tossed_message.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param graph_id: Graph id. Example: ``"AAMk-outlook-1"``
    :return: True if present. Example: ``False``
    """
    logger.info("tosser.index.already_tossed | entry | graph_id=%s", graph_id)
    raise NotImplementedError()


def record_tossed(conn: sqlite3.Connection, row: TossedMessage) -> None:
    """Insert TossedMessage.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param row: New row. Example: ``TossedMessage(...)``
    :return: None
    """
    logger.info("tosser.index.record_tossed | entry | graph_id=%s source=%s", row.graph_id, row.source)
    raise NotImplementedError()


def find_by_message_id(conn: sqlite3.Connection, message_id: str) -> TossedMessage | None:
    """Lookup by RFC822 Message-ID.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param message_id: Header value. Example: ``"<teams.mjqxg2a.abc@o365pop.local>"``
    :return: Row or None.
    """
    logger.info("tosser.index.find_by_message_id | entry | message_id=%s", message_id)
    raise NotImplementedError()


def upsert_chat_map(conn: sqlite3.Connection, chat_id: str, reply_address: str, chat_b32: str) -> None:
    """Remember chat → teams.* address.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param chat_id: Graph chat id. Example: ``"19:general"``
    :param reply_address: From address. Example: ``"teams.mjqxg2a@o365pop.local"``
    :param chat_b32: Encoded id. Example: ``"mjqxg2a"``
    :return: None
    """
    logger.info("tosser.index.upsert_chat_map | entry | chat_id=%s", chat_id)
    raise NotImplementedError()


def chat_id_for_address(conn: sqlite3.Connection, address: str) -> str | None:
    """Resolve teams.* address to chat_id.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param address: RFC822 address. Example: ``"teams.mjqxg2a@o365pop.local"``
    :return: chat_id or None. Example: ``"19:general"``
    """
    logger.info("tosser.index.chat_id_for_address | entry | address=%s", address)
    raise NotImplementedError()
