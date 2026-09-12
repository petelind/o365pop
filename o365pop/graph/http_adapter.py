"""HttpGraphAdapter — httpx calls to graph.microsoft.com/v1.0."""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
GRAPH_TIMEOUT = httpx.Timeout(300.0, connect=30.0)
CALENDAR_VIEW_SELECT = (
    "id,subject,start,end,isAllDay,location,bodyPreview,body,categories,attendees,"
    "isOrganizer,type,showAs,sensitivity,reminderMinutesBeforeStart,lastModifiedDateTime,hasAttachments"
)
PREFER_TEXT_BODY = 'outlook.body-content-type="text"'


class HttpGraphAdapter:
    """Bearer-authenticated Graph REST client.

    :param access_token: Bearer token. Example: ``"eyJ0..."``
    :param client: Optional httpx client. Example: ``httpx.Client()``
    """

    def __init__(self, access_token: str, client: httpx.Client | None = None) -> None:
        self._access_token = access_token
        self._client = client
        self._owns_client = client is None

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
        payload = base64.b64encode(rfc822)
        self._request("POST", "/me/sendMail", content=payload, content_type="text/plain")
        logger.info("HttpGraphAdapter.send_mime | exit | status=ok encoded_len=%s", len(payload))

    def post_chat_message(self, chat_id: str, text: str) -> None:
        """POST /chats/{id}/messages.

        :param chat_id: Graph chat id. Example: ``"19:general"``
        :param text: Body. Example: ``"On it"``
        :return: None
        """
        logger.info("HttpGraphAdapter.post_chat_message | entry | chat_id=%s", chat_id)
        self._request("POST", f"/chats/{chat_id}/messages", json_body={"body": {"content": text}})
        logger.info("HttpGraphAdapter.post_chat_message | exit | status=ok")

    def list_todo_lists(self) -> list[dict[str, Any]]:
        """GET /me/todo/lists.

        :return: Lists. Example: ``[{"id": "list-work"}]``
        """
        logger.info("HttpGraphAdapter.list_todo_lists | entry")
        rows = list((self._get_json("/me/todo/lists").get("value") or []))
        logger.info("HttpGraphAdapter.list_todo_lists | exit | count=%s", len(rows))
        return rows

    def list_todo_tasks(self, list_id: str) -> list[dict[str, Any]]:
        """GET /me/todo/lists/{id}/tasks.

        :param list_id: List id. Example: ``"list-work"``
        :return: Tasks. Example: ``[{"id": "task-q3"}]``
        """
        logger.info("HttpGraphAdapter.list_todo_tasks | entry | list_id=%s", list_id)
        rows = list((self._get_json(f"/me/todo/lists/{list_id}/tasks").get("value") or []))
        logger.info("HttpGraphAdapter.list_todo_tasks | exit | count=%s", len(rows))
        return rows

    def list_master_categories(self) -> list[dict[str, Any]]:
        """GET /me/outlook/masterCategories.

        :return: Categories. Example: ``[{"id": "cat-red"}]``
        """
        logger.info("HttpGraphAdapter.list_master_categories | entry")
        rows = list((self._get_json("/me/outlook/masterCategories").get("value") or []))
        logger.info("HttpGraphAdapter.list_master_categories | exit | count=%s", len(rows))
        return rows

    def patch_todo_task(self, list_id: str, task_id: str, body: dict[str, Any]) -> None:
        """PATCH /me/todo/lists/{listId}/tasks/{taskId}.

        :param list_id: List id. Example: ``"list-work"``
        :param task_id: Task id. Example: ``"task-q3"``
        :param body: Patch object. Example: ``{"status": "completed"}``
        :return: None
        """
        logger.info("HttpGraphAdapter.patch_todo_task | entry | list_id=%s task_id=%s", list_id, task_id)
        self._request("PATCH", f"/me/todo/lists/{list_id}/tasks/{task_id}", json_body=body)
        logger.info("HttpGraphAdapter.patch_todo_task | exit | status=ok")

    def delete_todo_task(self, list_id: str, task_id: str) -> None:
        """DELETE /me/todo/lists/{listId}/tasks/{taskId}.

        :param list_id: List id. Example: ``"list-work"``
        :param task_id: Task id. Example: ``"task-q3"``
        :return: None
        """
        logger.info("HttpGraphAdapter.delete_todo_task | entry | list_id=%s task_id=%s", list_id, task_id)
        self._request("DELETE", f"/me/todo/lists/{list_id}/tasks/{task_id}")
        logger.info("HttpGraphAdapter.delete_todo_task | exit | status=ok")

    def list_calendars(self) -> list[dict[str, Any]]:
        """GET /me/calendars skipping non-editable calendars.

        :return: Calendars. Example: ``[{"id": "cal-work", "displayName": "Work"}]``
        """
        logger.info("HttpGraphAdapter.list_calendars | entry")
        rows = self._collect_values("/me/calendars")
        editable = [row for row in rows if row.get("canEdit", True) is not False]
        logger.info("HttpGraphAdapter.list_calendars | exit | count=%s", len(editable))
        return editable

    def list_calendar_view(self, calendar_id: str, start: str, end: str) -> list[dict[str, Any]]:
        """GET /me/calendars/{id}/calendarView with @odata.nextLink pagination.

        :param calendar_id: Graph calendar id. Example: ``"cal-work"``
        :param start: Window start ISO. Example: ``"2026-08-12T00:00:00Z"``
        :param end: Window end ISO. Example: ``"2027-03-10T00:00:00Z"``
        :return: Events. Example: ``[{"id": "evt-standup"}]``
        """
        logger.info("HttpGraphAdapter.list_calendar_view | entry | calendar_id=%s prefer=text", calendar_id)
        query = f"startDateTime={start}&endDateTime={end}&$top=100&$select={CALENDAR_VIEW_SELECT}"
        path = f"/me/calendars/{calendar_id}/calendarView?{query}"
        rows = self._collect_values(path, extra_headers={"Prefer": PREFER_TEXT_BODY})
        logger.info("HttpGraphAdapter.list_calendar_view | exit | count=%s", len(rows))
        return rows

    def create_event(self, calendar_id: str, body: dict[str, Any]) -> dict[str, Any]:
        """POST /me/calendars/{id}/events.

        :param calendar_id: Target calendar. Example: ``"cal-work"``
        :param body: Event object. Example: ``{"subject": "Dentist"}``
        :return: Created event. Example: ``{"id": "evt-new"}``
        """
        logger.info("HttpGraphAdapter.create_event | entry | calendar_id=%s", calendar_id)
        response = self._request("POST", f"/me/calendars/{calendar_id}/events", json_body=body)
        payload = response.json()
        logger.info("HttpGraphAdapter.create_event | exit | event_id=%s", payload.get("id"))
        return payload if isinstance(payload, dict) else {"id": ""}

    def patch_event(self, event_id: str, body: dict[str, Any]) -> None:
        """PATCH /me/events/{id}.

        :param event_id: Graph event id. Example: ``"evt-standup"``
        :param body: Patch object. Example: ``{"subject": "Standup moved"}``
        :return: None
        """
        logger.info("HttpGraphAdapter.patch_event | entry | event_id=%s", event_id)
        self._request("PATCH", f"/me/events/{event_id}", json_body=body)
        logger.info("HttpGraphAdapter.patch_event | exit | status=ok")

    def delete_event(self, event_id: str) -> None:
        """DELETE /me/events/{id}.

        :param event_id: Graph event id. Example: ``"evt-standup"``
        :return: None
        """
        logger.info("HttpGraphAdapter.delete_event | entry | event_id=%s", event_id)
        self._request("DELETE", f"/me/events/{event_id}")
        logger.info("HttpGraphAdapter.delete_event | exit | status=ok")

    def list_event_attachments(self, event_id: str) -> list[dict[str, Any]]:
        """GET /me/events/{id}/attachments.

        :param event_id: Graph event id. Example: ``"evt-standup"``
        :return: Attachment dicts. Example: ``[{"id": "att-1", "name": "agenda.pdf"}]``
        """
        logger.info("HttpGraphAdapter.list_event_attachments | entry | event_id=%s", event_id)
        rows = list((self._get_json(f"/me/events/{event_id}/attachments").get("value") or []))
        logger.info("HttpGraphAdapter.list_event_attachments | exit | count=%s", len(rows))
        return rows

    def get_event_attachment_bytes(self, event_id: str, attachment_id: str) -> bytes:
        """GET /me/events/{id}/attachments/{attachmentId}/$value.

        :param event_id: Graph event id. Example: ``"evt-standup"``
        :param attachment_id: Attachment id. Example: ``"att-1"``
        :return: File bytes. Example: ``b"%PDF-1.4"``
        """
        logger.info(
            "HttpGraphAdapter.get_event_attachment_bytes | entry | event_id=%s attachment_id=%s",
            event_id,
            attachment_id,
        )
        response = self._request("GET", f"/me/events/{event_id}/attachments/{attachment_id}/$value")
        logger.info("HttpGraphAdapter.get_event_attachment_bytes | exit | bytes=%s", len(response.content))
        return response.content

    def create_event_attachment(self, event_id: str, name: str, content_type: str, content: bytes) -> dict[str, Any]:
        """POST /me/events/{id}/attachments.

        :param event_id: Graph event id. Example: ``"evt-standup"``
        :param name: File name. Example: ``"agenda.pdf"``
        :param content_type: MIME type. Example: ``"application/pdf"``
        :param content: Raw bytes. Example: ``b"%PDF-1.4"``
        :return: Created attachment. Example: ``{"id": "att-2", "name": "agenda.pdf"}``
        """
        logger.info("HttpGraphAdapter.create_event_attachment | entry | event_id=%s name=%s", event_id, name)
        payload = {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": name,
            "contentType": content_type,
            "contentBytes": base64.b64encode(content).decode("ascii"),
        }
        response = self._request("POST", f"/me/events/{event_id}/attachments", json_body=payload)
        body = response.json()
        logger.info("HttpGraphAdapter.create_event_attachment | exit | attachment_id=%s", body.get("id"))
        return body if isinstance(body, dict) else {"id": ""}

    def _get_json(self, path: str, extra_headers: dict[str, str] | None = None) -> dict[str, Any]:
        """GET a JSON Graph resource.

        :param path: URL path. Example: ``"/me/chats"``
        :param extra_headers: Extra request headers. Example: ``{"Prefer": PREFER_TEXT_BODY}``
        :return: Parsed object. Example: ``{"value": []}``
        """
        response = self._request("GET", path, extra_headers=extra_headers)
        payload = response.json()
        return payload if isinstance(payload, dict) else {"value": []}

    def _collect_values(self, path: str, extra_headers: dict[str, str] | None = None) -> list[dict[str, Any]]:
        """Follow ``@odata.nextLink`` until all pages are read.

        :param path: Initial Graph path. Example: ``"/me/calendars"``
        :param extra_headers: Extra request headers. Example: ``{"Prefer": PREFER_TEXT_BODY}``
        :return: Combined ``value`` rows. Example: ``[{"id": "evt-standup"}, ...]``
        """
        rows: list[dict[str, Any]] = []
        next_path: str | None = path
        pages = 0
        while next_path:
            payload = self._get_json(next_path, extra_headers=extra_headers)
            chunk = list(payload.get("value") or [])
            rows.extend(chunk)
            pages += 1
            link = payload.get("@odata.nextLink")
            next_path = _graph_path_from_next_link(str(link)) if link else None
        logger.info("HttpGraphAdapter._collect_values | exit | path=%s pages=%s count=%s", path, pages, len(rows))
        return rows

    def _request(
        self,
        method: str,
        path: str,
        *,
        content: bytes | None = None,
        json_body: dict[str, Any] | None = None,
        content_type: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Issue one Graph request with a bearer header.

        :param method: HTTP method. Example: ``"GET"``
        :param path: Absolute path. Example: ``"/me/sendMail"``
        :param content: Raw body. Example: ``b"Subject: Hi"``
        :param json_body: JSON body. Example: ``{"body": {"content": "On it"}}``
        :param content_type: Content-Type override. Example: ``"text/plain"``
        :param extra_headers: Extra request headers. Example: ``{"Prefer": PREFER_TEXT_BODY}``
        :return: Response. Example: ``<Response [200]>``
        """
        headers = {"Authorization": f"Bearer {self._access_token}"}
        if content_type:
            headers["Content-Type"] = content_type
        if extra_headers:
            headers.update(extra_headers)
        client = self._ensure_client()
        response = client.request(method, f"{GRAPH_ROOT}{path}", headers=headers, content=content, json=json_body)
        response.raise_for_status()
        return response

    def _ensure_client(self) -> httpx.Client:
        """Return a reusable httpx client for pagination-heavy calls.

        :return: Client. Example: ``httpx.Client(timeout=GRAPH_TIMEOUT)``
        """
        if self._client is None:
            self._client = httpx.Client(timeout=GRAPH_TIMEOUT)
        return self._client

    def close(self) -> None:
        """Close an adapter-owned httpx client.

        :return: None
        """
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None


def _graph_path_from_next_link(link: str) -> str:
    """Strip Graph host prefix from an ``@odata.nextLink`` URL.

    :param link: Full next page URL. Example: ``"https://graph.microsoft.com/v1.0/me/calendars?..."``
    :return: Path for ``_request``. Example: ``"/me/calendars?..."``
    """
    if link.startswith(GRAPH_ROOT):
        return link[len(GRAPH_ROOT) :]
    return link


def _http_chat_line(chat: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    """Flatten one chat message.

    :param chat: Chat resource. Example: ``{"id": "19:general", "topic": "general"}``
    :param row: Message resource. Example: ``{"id": "m1", "body": {"content": "Hi"}}``
    :return: Tosser dict. Example: ``{"chat_id": "19:general", "body": "Hi", "body_content_type": "html"}``
    """
    user = (row.get("from") or {}).get("user") or {}
    body = row.get("body") if isinstance(row.get("body"), dict) else {}
    chat_id = str(chat.get("id") or "")
    return {
        "chat_id": chat_id,
        "message_id": str(row.get("id") or ""),
        "from_name": str(user.get("displayName") or "Teams"),
        "body": str(body.get("content") or ""),
        "body_content_type": str(body.get("contentType") or "text"),
        "chat_subject": str(chat.get("topic") or chat_id),
    }
