"""Synthesize Teams RFC822 with reply-map headers (never a real SMTP From)."""

from __future__ import annotations

import logging
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def teams_to_rfc822(
    *,
    chat_id: str,
    graph_message_id: str,
    from_name: str,
    body: str,
    chat_subject: str,
) -> EmailMessage:
    """Build a tossed Teams message.

    :param chat_id: Graph chat id. Example: ``"19:general"``
    :param graph_message_id: Graph message id. Example: ``"abc"``
    :param from_name: Display name. Example: ``"Ada Lovelace"``
    :param body: Chat text. Example: ``"Ship it"``
    :param chat_subject: Chat title. Example: ``"general"``
    :return: EmailMessage with teams.* From/Reply-To and minted Message-ID.
    """
    logger.info(
        "tosser.mime_factory.teams_to_rfc822 | entry | chat_id=%s from_name=%s",
        chat_id,
        from_name,
    )
    # 1. reply_address(chat_id) for From and Reply-To
    # 2. Message-ID <teams.{chat_b32}.{msg_b32}@o365pop.local>
    # 3. Subject Teams: {chat}
    # 4. X-O365POP-Source / Chat-Id / Message-Id
    raise NotImplementedError()
