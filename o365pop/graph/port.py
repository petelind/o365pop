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

        :return: Dicts with chat_id, message_id, from_name, body. Example: ``[{"chat_id": "19:general", ...}]``
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
