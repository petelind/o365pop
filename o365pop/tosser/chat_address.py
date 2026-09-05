"""teams.{base32(chat_id)}@o365pop.local codec (SAO §2 reply map)."""

from __future__ import annotations

import base64
import logging
import re

logger = logging.getLogger(__name__)

LOCAL_DOMAIN = "o365pop.local"
_TEAMS_LOCAL = re.compile(r"^teams\.([a-z2-7]+)@" + re.escape(LOCAL_DOMAIN) + r"$", re.IGNORECASE)


def encode_chat_id(chat_id: str) -> str:
    """Lowercase base32, no padding.

    :param chat_id: Graph chat id. Example: ``"19:general@thread.v2"``
    :return: b32 token. Example: ``"gezdgnbq..."``
    :raises ValueError: if chat_id is empty
    """
    logger.info("tosser.chat_address.encode_chat_id | entry | chat_id=%s", chat_id)
    if not chat_id:
        raise ValueError("chat_id must not be empty")
    token = base64.b32encode(chat_id.encode("utf-8")).decode("ascii").rstrip("=").lower()
    logger.info("tosser.chat_address.encode_chat_id | exit | chat_b32=%s", token)
    return token


def decode_chat_b32(chat_b32: str) -> str:
    """Inverse of encode_chat_id.

    :param chat_b32: Encoded token. Example: ``"gezdgnbq..."``
    :return: Graph chat id. Example: ``"19:general@thread.v2"``
    :raises ValueError: if not valid base32
    """
    logger.info("tosser.chat_address.decode_chat_b32 | entry | chat_b32=%s", chat_b32)
    if not chat_b32:
        raise ValueError("chat_b32 must not be empty")
    padded = chat_b32.upper() + "=" * ((8 - len(chat_b32) % 8) % 8)
    try:
        chat_id = base64.b32decode(padded).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("chat_b32 is not valid base32") from exc
    logger.info("tosser.chat_address.decode_chat_b32 | exit | chat_id=%s", chat_id)
    return chat_id


def reply_address(chat_id: str) -> str:
    """Full From/Reply-To address for a chat.

    :param chat_id: Graph chat id. Example: ``"19:general"``
    :return: Address. Example: ``"teams.mjqxg2a@o365pop.local"``
    """
    logger.info("tosser.chat_address.reply_address | entry | chat_id=%s", chat_id)
    address = f"teams.{encode_chat_id(chat_id)}@{LOCAL_DOMAIN}"
    logger.info("tosser.chat_address.reply_address | exit | address=%s", address)
    return address


def parse_reply_address(address: str) -> str | None:
    """Extract chat_b32 from teams.*@o365pop.local, else None.

    :param address: RFC822 address. Example: ``"teams.mjqxg2a@o365pop.local"``
    :return: chat_b32 or None. Example: ``"mjqxg2a"``
    """
    logger.info("tosser.chat_address.parse_reply_address | entry | address=%s", address)
    cleaned = address.strip().lower()
    if cleaned.startswith("<") and cleaned.endswith(">"):
        cleaned = cleaned[1:-1]
    match = _TEAMS_LOCAL.match(cleaned)
    token = match.group(1) if match else None
    logger.info("tosser.chat_address.parse_reply_address | exit | chat_b32=%s", token)
    return token
