"""FileGraphAdapter — fixture JSON/MIME on disk (integration, no mocks)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FileGraphAdapter:
    """Read ``tests/fixtures/graph/<case>/``.

    :param case_dir: Fixture directory. Example: ``Path("tests/fixtures/graph/sync1_1")``
    """

    def __init__(self, case_dir: Path) -> None:
        self._case_dir = case_dir

    def list_inbox_messages(self) -> list[dict[str, Any]]:
        """Load inbox.json.

        :return: Message dicts. Example: ``[{"id": "AAMk-outlook-1"}]``
        """
        logger.info("FileGraphAdapter.list_inbox_messages | entry | case=%s", self._case_dir)
        raise NotImplementedError()

    def get_message_mime(self, message_id: str) -> bytes:
        """Load ``{message_id}.eml``.

        :param message_id: Graph id. Example: ``"AAMk-outlook-1"``
        :return: RFC822 bytes. Example: ``b"Subject: Q3 close\\r\\n"``
        """
        logger.info("FileGraphAdapter.get_message_mime | entry | message_id=%s", message_id)
        raise NotImplementedError()

    def list_new_chat_messages(self) -> list[dict[str, Any]]:
        """Load chats.json.

        :return: Chat lines. Example: ``[{"chat_id": "19:general", "body": "Ship it"}]``
        """
        logger.info("FileGraphAdapter.list_new_chat_messages | entry")
        raise NotImplementedError()

    def send_mime(self, rfc822: bytes) -> None:
        """Record posted MIME under the case dir.

        :param rfc822: Message bytes. Example: ``b"Subject: Hello Ada\\r\\n"``
        :return: None
        """
        logger.info("FileGraphAdapter.send_mime | entry | size=%s", len(rfc822))
        raise NotImplementedError()

    def post_chat_message(self, chat_id: str, text: str) -> None:
        """Record a chat post.

        :param chat_id: Graph chat id. Example: ``"19:general"``
        :param text: Body. Example: ``"On it"``
        :return: None
        """
        logger.info("FileGraphAdapter.post_chat_message | entry | chat_id=%s text_len=%s", chat_id, len(text))
        raise NotImplementedError()
