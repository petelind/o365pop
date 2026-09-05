"""HttpGraphAdapter — httpx calls to graph.microsoft.com/v1.0."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"


class HttpGraphAdapter:
    """Bearer-authenticated Graph REST client.

    :param access_token: Bearer token. Example: ``"eyJ0..."``
    :param client: Optional httpx client. Example: ``httpx.Client()``
    """

    def __init__(self, access_token: str, client: httpx.Client | None = None) -> None:
        self._access_token = access_token
        self._client = client

    def list_inbox_messages(self) -> list[dict[str, Any]]:
        """GET /me/mailFolders/inbox/messages.

        :return: Message dicts. Example: ``[{"id": "AAMk-1"}]``
        """
        logger.info("HttpGraphAdapter.list_inbox_messages | entry")
        raise NotImplementedError()

    def get_message_mime(self, message_id: str) -> bytes:
        """GET /me/messages/{id}/$value.

        :param message_id: Graph id. Example: ``"AAMk-1"``
        :return: RFC822 bytes. Example: ``b"From: ..."``
        """
        logger.info("HttpGraphAdapter.get_message_mime | entry | message_id=%s", message_id)
        raise NotImplementedError()

    def list_new_chat_messages(self) -> list[dict[str, Any]]:
        """GET /me/chats and per-chat messages.

        :return: Chat lines. Example: ``[{"chat_id": "19:general"}]``
        """
        logger.info("HttpGraphAdapter.list_new_chat_messages | entry")
        raise NotImplementedError()

    def send_mime(self, rfc822: bytes) -> None:
        """POST /me/sendMail text/plain MIME.

        :param rfc822: Message bytes. Example: ``b"Subject: Hello\\r\\n"``
        :return: None
        """
        logger.info("HttpGraphAdapter.send_mime | entry | size=%s", len(rfc822))
        raise NotImplementedError()

    def post_chat_message(self, chat_id: str, text: str) -> None:
        """POST /chats/{id}/messages.

        :param chat_id: Graph chat id. Example: ``"19:general"``
        :param text: Body. Example: ``"On it"``
        :return: None
        """
        logger.info("HttpGraphAdapter.post_chat_message | entry | chat_id=%s", chat_id)
        raise NotImplementedError()
