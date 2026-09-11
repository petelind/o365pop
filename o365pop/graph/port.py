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
