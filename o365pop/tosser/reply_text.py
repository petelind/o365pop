"""Extract the operator's reply above quoted Entourage history."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

QUOTE_MARKERS = (">", "From:", "-----Original Message-----")


def extract(body: str) -> str:
    """Return text before the first quote marker.

    :param body: Full SMTP body. Example: ``"On it\\n\\n> Ship it"``
    :return: Top part. Example: ``"On it"``
    """
    logger.info("tosser.reply_text.extract | entry | body_len=%s", len(body))
    cut = _first_quote_index(body)
    if cut is None:
        logger.info("tosser.reply_text.extract | branch | fallback=full_body")
        result = body.strip()
    else:
        result = body[:cut].strip()
        logger.info("tosser.reply_text.extract | processing | cut=%s text_len=%s", cut, len(result))
    logger.info("tosser.reply_text.extract | exit | text_len=%s", len(result))
    return result


def _first_quote_index(body: str) -> int | None:
    """Byte offset of the first quote-marker line, or None.

    :param body: Full SMTP body. Example: ``"On it\\n\\n> Ship it"``
    :return: Cut index or None. Example: ``6``
    """
    offset = 0
    for line in body.splitlines(keepends=True):
        stripped = line.lstrip()
        if any(stripped.startswith(marker) for marker in QUOTE_MARKERS):
            return offset
        offset += len(line)
    return None
