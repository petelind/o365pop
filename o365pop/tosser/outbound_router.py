"""Route spool RFC822 to sendMail or Teams chat (SAO §2 order)."""

from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import getaddresses

from o365pop.tosser.chat_address import LOCAL_DOMAIN
from o365pop.tosser.index import chat_id_for_address, find_by_message_id

logger = logging.getLogger(__name__)

_MESSAGE_ID = re.compile(r"<[^>]+>")
_LOCAL_SUFFIX = f"@{LOCAL_DOMAIN}"


@dataclass(frozen=True)
class Route:
    """Scanner decision.

    :param kind: send_mail|teams_chat|map_miss. Example: ``"teams_chat"``
    :param chat_id: Set when kind is teams_chat. Example: ``"19:general"``
    """

    kind: str
    chat_id: str | None = None


class OutboundRouter:
    """In-Reply-To → TossedMessage; else To teams.*; else sendMail; unknown @o365pop.local fail.

    :param conn: sqlite connection. Example: ``connect(path)``
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def route(self, message: EmailMessage) -> Route:
        """Decide Graph action.

        :param message: Parsed RFC822. Example: message with In-Reply-To teams.*
        :return: Route. Example: ``Route(kind="teams_chat", chat_id="19:general")``
        """
        logger.info("OutboundRouter.route | entry | subject=%s", message.get("Subject"))
        via_thread = self._route_from_reply_headers(message)
        decided = via_thread if via_thread is not None else self._route_from_recipients(message)
        logger.info(
            "OutboundRouter.route | branch | route=%s chat_id=%s",
            decided.kind,
            decided.chat_id,
        )
        logger.info("OutboundRouter.route | exit | route=%s", decided.kind)
        return decided

    def _route_from_reply_headers(self, message: EmailMessage) -> Route | None:
        """In-Reply-To / References vs TossedMessage source=teams.

        :param message: Parsed RFC822. Example: message with In-Reply-To teams.*
        :return: teams_chat route or None. Example: ``Route(kind="teams_chat", chat_id="19:general")``
        """
        for message_id in _header_message_ids(message):
            tossed = find_by_message_id(self._conn, message_id)
            if tossed is None or tossed.source != "teams" or not tossed.chat_id:
                logger.info(
                    "OutboundRouter.route | branch | reply_id=%s teams_hit=false",
                    message_id,
                )
                continue
            logger.info(
                "OutboundRouter.route | processing | reply_id=%s source=teams chat_id=%s",
                message_id,
                tossed.chat_id,
            )
            return Route(kind="teams_chat", chat_id=tossed.chat_id)
        return None

    def _route_from_recipients(self, message: EmailMessage) -> Route:
        """To/Cc via ChatMap, else map_miss for @o365pop.local, else send_mail.

        :param message: Parsed RFC822. Example: To teams.unknown@o365pop.local
        :return: Route. Example: ``Route(kind="map_miss")``
        """
        mapped: str | None = None
        local_miss = False
        for address in _recipient_addresses(message):
            chat_id = chat_id_for_address(self._conn, address)
            if chat_id:
                mapped = chat_id
                break
            if address.endswith(_LOCAL_SUFFIX):
                local_miss = True
        if mapped:
            return Route(kind="teams_chat", chat_id=mapped)
        if local_miss:
            return Route(kind="map_miss")
        return Route(kind="send_mail")


def _header_message_ids(message: EmailMessage) -> list[str]:
    """Collect Message-IDs from In-Reply-To and References.

    :param message: Parsed RFC822. Example: In-Reply-To ``<teams.mjqxg2a.abc@o365pop.local>``
    :return: Id list. Example: ``["<teams.mjqxg2a.abc@o365pop.local>"]``
    """
    ids: list[str] = []
    for header in ("In-Reply-To", "References"):
        raw = message.get(header)
        if not raw:
            continue
        found = _MESSAGE_ID.findall(str(raw))
        ids.extend(found if found else [str(raw).strip()])
    return ids


def _recipient_addresses(message: EmailMessage) -> list[str]:
    """Lowercased To/Cc mailbox addresses.

    :param message: Parsed RFC822. Example: To ``Ada <ada@example.com>``
    :return: Addresses. Example: ``["ada@example.com"]``
    """
    headers = message.get_all("To", []) + message.get_all("Cc", [])
    return [addr.lower() for _, addr in getaddresses(headers) if addr]
