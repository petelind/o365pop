"""Inbound tosser: Graph payloads → maildir + TossedMessage / ChatMap."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from o365pop.graph.port import GraphPort
from o365pop.mailstore.maildir import MaildirStore

logger = logging.getLogger(__name__)


class InboundTosser:
    """Drop Outlook MIME and Teams RFC822; skip graph_id duplicates.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param maildir: Maildir store. Example: ``MaildirStore(Path("var/maildir"))``
    :param graph: Graph port. Example: ``FileGraphAdapter(case_dir)``
    """

    def __init__(self, conn: sqlite3.Connection, maildir: MaildirStore, graph: GraphPort) -> None:
        self._conn = conn
        self._maildir = maildir
        self._graph = graph

    def toss_all(self) -> dict[str, int]:
        """Pull inbox + chats and toss new items.

        :return: Counts. Example: ``{"tossed": 1, "skipped_dup": 0}``
        """
        logger.info("InboundTosser.toss_all | entry")
        raise NotImplementedError()

    def toss_outlook(self, message: dict[str, Any]) -> bool:
        """Toss one Inbox message via $value MIME.

        :param message: Graph metadata. Example: ``{"id": "AAMk-outlook-1"}``
        :return: True if written. Example: ``True``
        """
        logger.info("InboundTosser.toss_outlook | entry | graph_id=%s", message.get("id"))
        raise NotImplementedError()

    def toss_teams(self, message: dict[str, Any]) -> bool:
        """Synthesize and toss one chat line; persist ChatMap.

        :param message: Chat line. Example: ``{"chat_id": "19:general", "body": "Ship it"}``
        :return: True if written. Example: ``True``
        """
        logger.info("InboundTosser.toss_teams | entry | chat_id=%s", message.get("chat_id"))
        raise NotImplementedError()
