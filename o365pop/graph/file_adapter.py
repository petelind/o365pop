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

    def list_todo_lists(self) -> list[dict[str, Any]]:
        """Load lists.json.

        :return: To Do lists. Example: ``[{"id": "list-work", "displayName": "Work"}]``
        """
        logger.info("FileGraphAdapter.list_todo_lists | entry | case=%s", self._case_dir)
        rows = _json_value(self._case_dir / "lists.json")
        logger.info("FileGraphAdapter.list_todo_lists | exit | count=%s", len(rows))
        return rows

    def list_todo_tasks(self, list_id: str) -> list[dict[str, Any]]:
        """Load tasks.json filtered by listId.

        :param list_id: To Do list id. Example: ``"list-work"``
        :return: Tasks. Example: ``[{"id": "task-q3", "title": "File the Q3 report"}]``
        """
        logger.info("FileGraphAdapter.list_todo_tasks | entry | list_id=%s", list_id)
        rows = [row for row in _json_value(self._case_dir / "tasks.json") if str(row.get("listId") or "") == list_id]
        logger.info("FileGraphAdapter.list_todo_tasks | exit | count=%s", len(rows))
        return rows

    def list_master_categories(self) -> list[dict[str, Any]]:
        """Load categories.json.

        :return: Categories. Example: ``[{"id": "cat-red", "color": "preset1"}]``
        """
        logger.info("FileGraphAdapter.list_master_categories | entry")
        rows = _json_value(self._case_dir / "categories.json")
        logger.info("FileGraphAdapter.list_master_categories | exit | count=%s", len(rows))
        return rows

    def patch_todo_task(self, list_id: str, task_id: str, body: dict[str, Any]) -> None:
        """Record a PATCH under patched.json.

        :param list_id: List id. Example: ``"list-work"``
        :param task_id: Task id. Example: ``"task-q3"``
        :param body: Patch object. Example: ``{"status": "completed"}``
        :return: None
        """
        logger.info("FileGraphAdapter.patch_todo_task | entry | list_id=%s task_id=%s", list_id, task_id)
        _append_json(self._case_dir / "patched.json", {"listId": list_id, "taskId": task_id, "body": body})
        logger.info("FileGraphAdapter.patch_todo_task | exit | status=recorded")

    def delete_todo_task(self, list_id: str, task_id: str) -> None:
        """Record a DELETE under deleted.json.

        :param list_id: List id. Example: ``"list-work"``
        :param task_id: Task id. Example: ``"task-q3"``
        :return: None
        """
        logger.info("FileGraphAdapter.delete_todo_task | entry | list_id=%s task_id=%s", list_id, task_id)
        _append_json(self._case_dir / "deleted.json", {"listId": list_id, "taskId": task_id})
        logger.info("FileGraphAdapter.delete_todo_task | exit | status=recorded")

    def list_calendars(self) -> list[dict[str, Any]]:
        """Load calendars.json.

        :return: Calendars. Example: ``[{"id": "cal-work", "displayName": "Work"}]``
        """
        logger.info("FileGraphAdapter.list_calendars | entry | case=%s", self._case_dir)
        rows = _json_value(self._case_dir / "calendars.json")
        logger.info("FileGraphAdapter.list_calendars | exit | count=%s", len(rows))
        return rows

    def list_calendar_view(self, calendar_id: str, start: str, end: str) -> list[dict[str, Any]]:
        """Load events.json filtered by calendarId.

        :param calendar_id: Graph calendar id. Example: ``"cal-work"``
        :param start: Window start ISO. Example: ``"2026-08-12T00:00:00Z"``
        :param end: Window end ISO. Example: ``"2027-03-10T00:00:00Z"``
        :return: Events. Example: ``[{"id": "evt-standup", "subject": "Standup"}]``
        """
        logger.info("FileGraphAdapter.list_calendar_view | entry | calendar_id=%s", calendar_id)
        rows = [
            row
            for row in _json_value(self._case_dir / "events.json")
            if str(row.get("calendarId") or row.get("calendar_id") or "") == calendar_id
        ]
        logger.info("FileGraphAdapter.list_calendar_view | exit | count=%s", len(rows))
        return rows

    def create_event(self, calendar_id: str, body: dict[str, Any]) -> dict[str, Any]:
        """Record a POST under created_events.json.

        :param calendar_id: Target calendar. Example: ``"cal-work"``
        :param body: Event object. Example: ``{"subject": "Dentist"}``
        :return: Created event with synthetic id. Example: ``{"id": "evt-created-1"}``
        """
        logger.info("FileGraphAdapter.create_event | entry | calendar_id=%s", calendar_id)
        created_id = f"evt-created-{len(_json_value(self._case_dir / 'created_events.json')) + 1}"
        row = {"id": created_id, "calendarId": calendar_id, **body}
        _append_json(self._case_dir / "created_events.json", row)
        logger.info("FileGraphAdapter.create_event | exit | event_id=%s", created_id)
        return row

    def patch_event(self, event_id: str, body: dict[str, Any]) -> None:
        """Record a PATCH under calendar_patched.json.

        :param event_id: Graph event id. Example: ``"evt-standup"``
        :param body: Patch object. Example: ``{"subject": "Standup moved"}``
        :return: None
        """
        logger.info("FileGraphAdapter.patch_event | entry | event_id=%s", event_id)
        _append_json(self._case_dir / "calendar_patched.json", {"eventId": event_id, "body": body})
        logger.info("FileGraphAdapter.patch_event | exit | status=recorded")

    def delete_event(self, event_id: str) -> None:
        """Record a DELETE under calendar_deleted.json.

        :param event_id: Graph event id. Example: ``"evt-standup"``
        :return: None
        """
        logger.info("FileGraphAdapter.delete_event | entry | event_id=%s", event_id)
        _append_json(self._case_dir / "calendar_deleted.json", {"eventId": event_id})
        logger.info("FileGraphAdapter.delete_event | exit | status=recorded")

    def list_event_attachments(self, event_id: str) -> list[dict[str, Any]]:
        """Load attachment metadata from events.json or attachments.json.

        :param event_id: Graph event id. Example: ``"evt-standup"``
        :return: Attachment dicts. Example: ``[{"id": "att-1", "name": "agenda.pdf"}]``
        """
        logger.info("FileGraphAdapter.list_event_attachments | entry | event_id=%s", event_id)
        for row in _json_value(self._case_dir / "events.json"):
            if str(row.get("id") or "") == event_id:
                attachments = row.get("attachments") or []
                if isinstance(attachments, list):
                    logger.info("FileGraphAdapter.list_event_attachments | exit | count=%s", len(attachments))
                    return list(attachments)
        rows = [
            row
            for row in _json_value(self._case_dir / "attachments.json")
            if str(row.get("eventId") or row.get("event_id") or "") == event_id
        ]
        logger.info("FileGraphAdapter.list_event_attachments | exit | count=%s", len(rows))
        return rows

    def get_event_attachment_bytes(self, event_id: str, attachment_id: str) -> bytes:
        """Load bytes from attachments/{eventId}/{name}.

        :param event_id: Graph event id. Example: ``"evt-standup"``
        :param attachment_id: Attachment id. Example: ``"att-1"``
        :return: File bytes. Example: ``b"%PDF-1.4"``
        """
        logger.info(
            "FileGraphAdapter.get_event_attachment_bytes | entry | event_id=%s attachment_id=%s",
            event_id,
            attachment_id,
        )
        name = attachment_id
        for row in self.list_event_attachments(event_id):
            if str(row.get("id") or "") == attachment_id:
                name = str(row.get("name") or attachment_id)
                break
        path = self._case_dir / "attachments" / event_id / name
        data = path.read_bytes()
        logger.info("FileGraphAdapter.get_event_attachment_bytes | exit | bytes=%s", len(data))
        return data

    def create_event_attachment(self, event_id: str, name: str, content_type: str, content: bytes) -> dict[str, Any]:
        """Record attachment POST under calendar_attachments_posted.json.

        :param event_id: Graph event id. Example: ``"evt-standup"``
        :param name: File name. Example: ``"agenda.pdf"``
        :param content_type: MIME type. Example: ``"application/pdf"``
        :param content: Raw bytes. Example: ``b"%PDF-1.4"``
        :return: Created attachment. Example: ``{"id": "att-post-1", "name": "agenda.pdf"}``
        """
        logger.info("FileGraphAdapter.create_event_attachment | entry | event_id=%s name=%s", event_id, name)
        posted = _json_value(self._case_dir / "calendar_attachments_posted.json")
        att_id = f"att-post-{len(posted) + 1}"
        dest = self._case_dir / "attachments" / event_id / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        row = {"id": att_id, "eventId": event_id, "name": name, "contentType": content_type, "bytes": len(content)}
        _append_json(self._case_dir / "calendar_attachments_posted.json", row)
        logger.info("FileGraphAdapter.create_event_attachment | exit | attachment_id=%s", att_id)
        return row


def _append_json(path: Path, row: dict[str, Any]) -> None:
    """Append one object to a JSON array file.

    :param path: Target file. Example: ``Path("patched.json")``
    :param row: Record. Example: ``{"taskId": "task-q3"}``
    :return: None
    """
    rows = json.loads(path.read_text()) if path.is_file() else []
    rows.append(row)
    path.write_text(json.dumps(rows))


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
    :return: Flat dict. Example: ``{"chat_id": "19:general", "body": "Ship it", "body_content_type": "text"}``
    """
    chat_id = str(row.get("chatId") or row.get("chat_id") or "")
    user = (row.get("from") or {}).get("user") or {}
    body = row.get("body") if isinstance(row.get("body"), dict) else {}
    return {
        "chat_id": chat_id,
        "message_id": str(row.get("id") or ""),
        "from_name": str(user.get("displayName") or "Teams"),
        "body": str(body.get("content") or row.get("body") or ""),
        "body_content_type": str(body.get("contentType") or "text"),
        "chat_subject": str(topics.get(chat_id) or chat_id),
    }
