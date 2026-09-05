"""Route spool RFC822 to sendMail or Teams chat (SAO §2 order)."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from email.message import EmailMessage

logger = logging.getLogger(__name__)


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
        # 1. In-Reply-To / References vs TossedMessage source=teams
        # 2. To/Cc teams.*@o365pop.local via ChatMap
        # 3. Any other @o365pop.local → map_miss
        # 4. Else send_mail
        raise NotImplementedError()
