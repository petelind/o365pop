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
        payload = self._get_json("/me/mailFolders/inbox/messages")
        rows = list(payload.get("value") or [])
        logger.info("HttpGraphAdapter.list_inbox_messages | exit | count=%s", len(rows))
        return rows

    def get_message_mime(self, message_id: str) -> bytes:
        """GET /me/messages/{id}/$value.

        :param message_id: Graph id. Example: ``"AAMk-1"``
        :return: RFC822 bytes. Example: ``b"From: ..."``
        """
        logger.info("HttpGraphAdapter.get_message_mime | entry | message_id=%s", message_id)
        response = self._request("GET", f"/me/messages/{message_id}/$value")
        logger.info("HttpGraphAdapter.get_message_mime | exit | bytes=%s", len(response.content))
        return response.content

    def list_new_chat_messages(self) -> list[dict[str, Any]]:
        """GET /me/chats and per-chat messages.

        :return: Chat lines. Example: ``[{"chat_id": "19:general"}]``
        """
        logger.info("HttpGraphAdapter.list_new_chat_messages | entry")
        chats = list((self._get_json("/me/chats").get("value") or []))
        lines: list[dict[str, Any]] = []
        for chat in chats:
            chat_id = str(chat.get("id") or "")
            messages = self._get_json(f"/me/chats/{chat_id}/messages")
            for row in messages.get("value") or []:
                lines.append(_http_chat_line(chat, row))
        logger.info("HttpGraphAdapter.list_new_chat_messages | exit | count=%s", len(lines))
        return lines

    def send_mime(self, rfc822: bytes) -> None:
        """POST /me/sendMail text/plain MIME.

        :param rfc822: Message bytes. Example: ``b"Subject: Hello\\r\\n"``
        :return: None
        """
        logger.info("HttpGraphAdapter.send_mime | entry | size=%s", len(rfc822))
        self._request("POST", "/me/sendMail", content=rfc822, content_type="text/plain")
        logger.info("HttpGraphAdapter.send_mime | exit | status=ok")

    def post_chat_message(self, chat_id: str, text: str) -> None:
        """POST /chats/{id}/messages.

        :param chat_id: Graph chat id. Example: ``"19:general"``
        :param text: Body. Example: ``"On it"``
        :return: None
        """
        logger.info("HttpGraphAdapter.post_chat_message | entry | chat_id=%s", chat_id)
        self._request("POST", f"/chats/{chat_id}/messages", json_body={"body": {"content": text}})
        logger.info("HttpGraphAdapter.post_chat_message | exit | status=ok")

    def _get_json(self, path: str) -> dict[str, Any]:
        """GET a JSON Graph resource.

        :param path: URL path. Example: ``"/me/chats"``
        :return: Parsed object. Example: ``{"value": []}``
        """
        response = self._request("GET", path)
        payload = response.json()
        return payload if isinstance(payload, dict) else {"value": []}

    def _request(
        self,
        method: str,
        path: str,
        *,
        content: bytes | None = None,
        json_body: dict[str, Any] | None = None,
        content_type: str | None = None,
    ) -> httpx.Response:
        """Issue one Graph request with a bearer header.

        :param method: HTTP method. Example: ``"GET"``
        :param path: Absolute path. Example: ``"/me/sendMail"``
        :param content: Raw body. Example: ``b"Subject: Hi"``
        :param json_body: JSON body. Example: ``{"body": {"content": "On it"}}``
        :param content_type: Content-Type override. Example: ``"text/plain"``
        :return: Response. Example: ``<Response [200]>``
        """
        headers = {"Authorization": f"Bearer {self._access_token}"}
        if content_type:
            headers["Content-Type"] = content_type
        client = self._client or httpx.Client()
        owns = self._client is None
        try:
            response = client.request(method, f"{GRAPH_ROOT}{path}", headers=headers, content=content, json=json_body)
            response.raise_for_status()
            return response
        finally:
            if owns:
                client.close()


def _http_chat_line(chat: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    """Flatten one chat message.

    :param chat: Chat resource. Example: ``{"id": "19:general", "topic": "general"}``
    :param row: Message resource. Example: ``{"id": "m1", "body": {"content": "Hi"}}``
    :return: Tosser dict. Example: ``{"chat_id": "19:general", "body": "Hi"}``
    """
    user = (row.get("from") or {}).get("user") or {}
    body = row.get("body") if isinstance(row.get("body"), dict) else {}
    chat_id = str(chat.get("id") or "")
    return {
        "chat_id": chat_id,
        "message_id": str(row.get("id") or ""),
        "from_name": str(user.get("displayName") or "Teams"),
        "body": str(body.get("content") or ""),
        "chat_subject": str(chat.get("topic") or chat_id),
    }
