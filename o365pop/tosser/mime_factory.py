"""Synthesize Teams RFC822 with reply-map headers (never a real SMTP From)."""

from __future__ import annotations

import logging
from email.message import EmailMessage

from o365pop.tosser.chat_address import LOCAL_DOMAIN, encode_chat_id, reply_address

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
    address = reply_address(chat_id)
    chat_b32 = encode_chat_id(chat_id)
    msg_b32 = encode_chat_id(graph_message_id)
    message = EmailMessage()
    message["From"] = f'"{from_name}" <{address}>'
    message["Reply-To"] = address
    message["To"] = "me@o365pop.local"
    message["Subject"] = f"Teams: {chat_subject}"
    message["Message-ID"] = f"<teams.{chat_b32}.{msg_b32}@{LOCAL_DOMAIN}>"
    message["X-O365POP-Source"] = "teams"
    message["X-O365POP-Chat-Id"] = chat_id
    message["X-O365POP-Message-Id"] = graph_message_id
    message.set_content(body)
    logger.info("tosser.mime_factory.teams_to_rfc822 | exit | message_id=%s", message["Message-ID"])
    return message
