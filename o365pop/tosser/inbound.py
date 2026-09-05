"""Inbound tosser: Graph payloads → maildir + TossedMessage / ChatMap."""

from __future__ import annotations

import email
import logging
import sqlite3
from email.header import decode_header, make_header
from typing import Any

from o365pop.graph.port import GraphPort
from o365pop.mailstore.maildir import MaildirStore
from o365pop.tosser.index import TossedMessage, already_tossed, record_tossed

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
        tossed = 0
        skipped = 0
        for message in self._graph.list_inbox_messages():
            if self.toss_outlook(message):
                tossed += 1
            else:
                skipped += 1
        for message in self._graph.list_new_chat_messages():
            if self.toss_teams(message):
                tossed += 1
            else:
                skipped += 1
        logger.info(
            "InboundTosser.toss_all | processing | tossed=%s skipped_dup=%s",
            tossed,
            skipped,
        )
        logger.info("InboundTosser.toss_all | exit | tossed=%s skipped_dup=%s", tossed, skipped)
        return {"tossed": tossed, "skipped_dup": skipped}

    def toss_outlook(self, message: dict[str, Any]) -> bool:
        """Toss one Inbox message via $value MIME.

        :param message: Graph metadata. Example: ``{"id": "AAMk-outlook-1"}``
        :return: True if written. Example: ``True``
        """
        graph_id = str(message.get("id") or "")
        logger.info("InboundTosser.toss_outlook | entry | graph_id=%s", graph_id)
        if not graph_id or already_tossed(self._conn, graph_id):
            logger.info("InboundTosser.toss_outlook | branch | skipped_dup=true graph_id=%s", graph_id)
            return False
        rfc822 = self._graph.get_message_mime(graph_id)
        uidl = f"uid-outlook-{graph_id}"
        self._maildir.add(rfc822, uidl)
        record_tossed(
            self._conn,
            TossedMessage(
                graph_id=graph_id,
                source="outlook",
                message_id=_message_id_from_mime(rfc822) or f"<outlook.{graph_id}@o365pop.local>",
                chat_id=None,
                uidl=uidl,
            ),
        )
        logger.info("InboundTosser.toss_outlook | exit | tossed=true graph_id=%s", graph_id)
        return True

    def toss_teams(self, message: dict[str, Any]) -> bool:
        """Synthesize and toss one chat line; persist ChatMap.

        :param message: Chat line. Example: ``{"chat_id": "19:general", "body": "Ship it"}``
        :return: True if written. Example: ``True``
        """
        logger.info("InboundTosser.toss_teams | entry | chat_id=%s", message.get("chat_id"))
        raise NotImplementedError()


def subject_of(rfc822: bytes) -> str:
    """Decode Subject from RFC822 bytes.

    :param rfc822: Message bytes. Example: ``b"Subject: Q3 close\\r\\n"``
    :return: Subject. Example: ``"Q3 close"``
    """
    parsed = email.message_from_bytes(rfc822)
    raw = parsed.get("Subject", "")
    return str(make_header(decode_header(raw))) if raw else ""


def _message_id_from_mime(rfc822: bytes) -> str:
    """Read Message-ID header or empty.

    :param rfc822: Message bytes. Example: ``b"Message-ID: <a@b>\\r\\n"``
    :return: Header value. Example: ``"<a@b>"``
    """
    parsed = email.message_from_bytes(rfc822)
    return str(parsed.get("Message-ID") or "").strip()
