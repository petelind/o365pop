"""FileGraphAdapter — fixture JSON/MIME on disk (integration, no mocks)."""

from __future__ import annotations

import json
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
        rows = _json_value(self._case_dir / "inbox.json")
        logger.info("FileGraphAdapter.list_inbox_messages | exit | count=%s", len(rows))
        return rows

    def get_message_mime(self, message_id: str) -> bytes:
        """Load ``{message_id}.eml`` or ``message.eml``.

        :param message_id: Graph id. Example: ``"AAMk-outlook-1"``
        :return: RFC822 bytes. Example: ``b"Subject: Q3 close\\r\\n"``
        """
        logger.info("FileGraphAdapter.get_message_mime | entry | message_id=%s", message_id)
        named = self._case_dir / f"{message_id}.eml"
        fallback = self._case_dir / "message.eml"
        path = named if named.is_file() else fallback
        data = path.read_bytes()
        logger.info("FileGraphAdapter.get_message_mime | exit | bytes=%s", len(data))
        return data

    def list_new_chat_messages(self) -> list[dict[str, Any]]:
        """Load chats.json + messages.json into tosser rows.

        :return: Chat lines. Example: ``[{"chat_id": "19:general", "body": "Ship it"}]``
        """
        logger.info("FileGraphAdapter.list_new_chat_messages | entry")
        topics = {
            row.get("id"): row.get("topic") or row.get("id") for row in _json_value(self._case_dir / "chats.json")
        }
        lines = [_flatten_chat(row, topics) for row in _json_value(self._case_dir / "messages.json")]
        logger.info("FileGraphAdapter.list_new_chat_messages | exit | count=%s", len(lines))
        return lines

    def send_mime(self, rfc822: bytes) -> None:
        """Record posted MIME under the case dir.

        :param rfc822: Message bytes. Example: ``b"Subject: Hello Ada\\r\\n"``
        :return: None
        """
        logger.info("FileGraphAdapter.send_mime | entry | size=%s", len(rfc822))
        (self._case_dir / "sent.eml").write_bytes(rfc822)
        logger.info("FileGraphAdapter.send_mime | exit | status=recorded")

    def post_chat_message(self, chat_id: str, text: str) -> None:
        """Record a chat post.

        :param chat_id: Graph chat id. Example: ``"19:general"``
        :param text: Body. Example: ``"On it"``
        :return: None
        """
        logger.info("FileGraphAdapter.post_chat_message | entry | chat_id=%s text_len=%s", chat_id, len(text))
        path = self._case_dir / "posted.json"
        rows = json.loads(path.read_text()) if path.is_file() else []
        rows.append({"chat_id": chat_id, "text": text})
        path.write_text(json.dumps(rows))
        logger.info("FileGraphAdapter.post_chat_message | exit | status=recorded")


def _json_value(path: Path) -> list[dict[str, Any]]:
    """Read a Graph-like ``{value: [...]}`` file; missing file is empty.

    :param path: JSON path. Example: ``Path("inbox.json")``
    :return: Value list. Example: ``[{"id": "AAMk-outlook-1"}]``
    """
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return list(payload.get("value") or [])
    return []


def _flatten_chat(row: dict[str, Any], topics: dict[Any, Any]) -> dict[str, Any]:
    """Normalize a Graph chat message for the tosser.

    :param row: messages.json item. Example: ``{"id": "teams-msg-1", "chatId": "19:general"}``
    :param topics: chat id → topic. Example: ``{"19:general": "general"}``
    :return: Flat dict. Example: ``{"chat_id": "19:general", "body": "Ship it"}``
    """
    chat_id = str(row.get("chatId") or row.get("chat_id") or "")
    user = (row.get("from") or {}).get("user") or {}
    body = row.get("body") if isinstance(row.get("body"), dict) else {}
    return {
        "chat_id": chat_id,
        "message_id": str(row.get("id") or ""),
        "from_name": str(user.get("displayName") or "Teams"),
        "body": str(body.get("content") or row.get("body") or ""),
        "chat_subject": str(topics.get(chat_id) or chat_id),
    }
