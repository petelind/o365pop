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
    raise NotImplementedError()
