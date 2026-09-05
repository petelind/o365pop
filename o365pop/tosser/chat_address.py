"""teams.{base32(chat_id)}@o365pop.local codec (SAO §2 reply map)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

LOCAL_DOMAIN = "o365pop.local"


def encode_chat_id(chat_id: str) -> str:
    """Lowercase base32, no padding.

    :param chat_id: Graph chat id. Example: ``"19:general@thread.v2"``
    :return: b32 token. Example: ``"gezdgnbq..."``
    :raises ValueError: if chat_id is empty
    """
    logger.info("tosser.chat_address.encode_chat_id | entry | chat_id=%s", chat_id)
    raise NotImplementedError()


def decode_chat_b32(chat_b32: str) -> str:
    """Inverse of encode_chat_id.

    :param chat_b32: Encoded token. Example: ``"gezdgnbq..."``
    :return: Graph chat id. Example: ``"19:general@thread.v2"``
    :raises ValueError: if not valid base32
    """
    logger.info("tosser.chat_address.decode_chat_b32 | entry | chat_b32=%s", chat_b32)
    raise NotImplementedError()


def reply_address(chat_id: str) -> str:
    """Full From/Reply-To address for a chat.

    :param chat_id: Graph chat id. Example: ``"19:general"``
    :return: Address. Example: ``"teams.mjqxg2a@o365pop.local"``
    """
    logger.info("tosser.chat_address.reply_address | entry | chat_id=%s", chat_id)
    raise NotImplementedError()


def parse_reply_address(address: str) -> str | None:
    """Extract chat_b32 from teams.*@o365pop.local, else None.

    :param address: RFC822 address. Example: ``"teams.mjqxg2a@o365pop.local"``
    :return: chat_b32 or None. Example: ``"mjqxg2a"``
    """
    logger.info("tosser.chat_address.parse_reply_address | entry | address=%s", address)
    raise NotImplementedError()
