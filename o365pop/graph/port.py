"""Graph REST port (SYNC). Implementations: HttpGraphAdapter, FileGraphAdapter."""

from __future__ import annotations

from typing import Any, Protocol


class GraphPort(Protocol):
    """Honest Graph REST operations. Daemons must not import this module."""

    def list_inbox_messages(self) -> list[dict[str, Any]]:
        """List Inbox message metadata.

        :return: Message dicts with id/subject. Example: ``[{"id": "AAMk-outlook-1", "subject": "Q3 close"}]``
        """
        ...

    def get_message_mime(self, message_id: str) -> bytes:
        """GET /me/messages/{id}/$value.

        :param message_id: Graph id. Example: ``"AAMk-outlook-1"``
        :return: RFC822 bytes. Example: ``b"Subject: Q3 close\\r\\n..."``
        """
        ...

    def list_new_chat_messages(self) -> list[dict[str, Any]]:
        """New Teams chat lines.

        :return: Chat line dicts. Example: ``[{"chat_id": "19:general", "body_content_type": "html"}]``
        """
        ...

    def send_mime(self, rfc822: bytes) -> None:
        """POST /me/sendMail with raw MIME (SMTP).

        :param rfc822: Message bytes. Example: ``b"Subject: Hello Ada\\r\\n..."``
        :return: None
        """
        ...

    def post_chat_message(self, chat_id: str, text: str) -> None:
        """POST /chats/{id}/messages (TEAM).

        :param chat_id: Graph chat id. Example: ``"19:general"``
        :param text: Reply body. Example: ``"On it"``
        :return: None
        """
        ...

    def list_todo_lists(self) -> list[dict[str, Any]]:
        """GET /me/todo/lists.

        :return: List dicts. Example: ``[{"id": "list-work", "displayName": "Work"}]``
        """
        ...

    def list_todo_tasks(self, list_id: str) -> list[dict[str, Any]]:
        """GET /me/todo/lists/{id}/tasks.

        :param list_id: To Do list id. Example: ``"list-work"``
        :return: Task dicts. Example: ``[{"id": "task-q3", "title": "File the Q3 report"}]``
        """
        ...

    def list_master_categories(self) -> list[dict[str, Any]]:
        """GET /me/outlook/masterCategories.

        :return: Category dicts. Example: ``[{"id": "cat-red", "displayName": "Urgent", "color": "preset1"}]``
        """
        ...

    def patch_todo_task(self, list_id: str, task_id: str, body: dict[str, Any]) -> None:
        """PATCH /me/todo/lists/{listId}/tasks/{taskId}.

        :param list_id: List id. Example: ``"list-work"``
        :param task_id: Task id. Example: ``"task-q3"``
        :param body: Patch object. Example: ``{"status": "completed"}``
        :return: None
        """
        ...

    def delete_todo_task(self, list_id: str, task_id: str) -> None:
        """DELETE /me/todo/lists/{listId}/tasks/{taskId}.

        :param list_id: List id. Example: ``"list-work"``
        :param task_id: Task id. Example: ``"task-q3"``
        :return: None
        """
        ...

    def list_calendars(self) -> list[dict[str, Any]]:
        """GET /me/calendars (editable mailbox calendars only in live adapter).

        :return: Calendar dicts. Example: ``[{"id": "cal-work", "displayName": "Work"}]``
        """
        ...

    def list_calendar_view(self, calendar_id: str, start: str, end: str) -> list[dict[str, Any]]:
        """GET /me/calendars/{id}/calendarView.

        :param calendar_id: Graph calendar id. Example: ``"cal-work"``
        :param start: Window start ISO. Example: ``"2026-08-12T00:00:00Z"``
        :param end: Window end ISO. Example: ``"2027-03-10T00:00:00Z"``
        :return: Event dicts. Example: ``[{"id": "evt-standup", "subject": "Standup"}]``
        """
        ...

    def create_event(self, calendar_id: str, body: dict[str, Any]) -> dict[str, Any]:
        """POST /me/calendars/{id}/events.

        :param calendar_id: Target calendar. Example: ``"cal-work"``
        :param body: Event object. Example: ``{"subject": "Dentist"}``
        :return: Created event. Example: ``{"id": "evt-new", "subject": "Dentist"}``
        """
        ...

    def patch_event(self, event_id: str, body: dict[str, Any]) -> None:
        """PATCH /me/events/{id}.

        :param event_id: Graph event id. Example: ``"evt-standup"``
        :param body: Patch object. Example: ``{"subject": "Standup moved"}``
        :return: None
        """
        ...

    def delete_event(self, event_id: str) -> None:
        """DELETE /me/events/{id}.

        :param event_id: Graph event id. Example: ``"evt-standup"``
        :return: None
        """
        ...

    def list_event_attachments(self, event_id: str) -> list[dict[str, Any]]:
        """GET /me/events/{id}/attachments metadata.

        :param event_id: Graph event id. Example: ``"evt-standup"``
        :return: Attachment dicts. Example: ``[{"id": "att-1", "name": "agenda.pdf"}]``
        """
        ...

    def get_event_attachment_bytes(self, event_id: str, attachment_id: str) -> bytes:
        """GET /me/events/{id}/attachments/{attachmentId}/$value.

        :param event_id: Graph event id. Example: ``"evt-standup"``
        :param attachment_id: Attachment id. Example: ``"att-1"``
        :return: File bytes. Example: ``b"%PDF-1.4"``
        """
        ...

    def create_event_attachment(self, event_id: str, name: str, content_type: str, content: bytes) -> dict[str, Any]:
        """POST /me/events/{id}/attachments.

        :param event_id: Graph event id. Example: ``"evt-standup"``
        :param name: File name. Example: ``"agenda.pdf"``
        :param content_type: MIME type. Example: ``"application/pdf"``
        :param content: Raw bytes. Example: ``b"%PDF-1.4"``
        :return: Created attachment. Example: ``{"id": "att-2", "name": "agenda.pdf"}``
        """
        ...
