"""Entourage Apple Event port. CI uses FakeEntourage; live uses OsascriptEntourage."""

from __future__ import annotations

from typing import Any, Protocol


class EntouragePort(Protocol):
    """In-memory or osascript Entourage surface. No Graph imports."""

    def list_tasks(self) -> list[dict[str, Any]]:
        """Return task records.

        :return: Task dicts. Example: ``[{"id": "1", "name": "File the Q3 report"}]``
        """
        ...

    def list_projects(self) -> list[dict[str, Any]]:
        """Return project records.

        :return: Project dicts. Example: ``[{"id": "10", "name": "Work"}]``
        """
        ...

    def list_categories(self) -> list[dict[str, Any]]:
        """Return category records.

        :return: Category dicts. Example: ``[{"id": "builtin-work", "name": "Work"}]``
        """
        ...

    def create_task(self, properties: dict[str, Any]) -> dict[str, Any]:
        """Create a task.

        :param properties: Name, due, content, project_id, categories. Example: ``{"name": "File the Q3 report"}``
        :return: Created record. Example: ``{"id": "1", "name": "File the Q3 report"}``
        """
        ...

    def update_task(self, task_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Patch a task.

        :param task_id: Entourage id. Example: ``"1"``
        :param properties: Fields to set. Example: ``{"completed": True}``
        :return: Updated record. Example: ``{"id": "1", "completed": True}``
        """
        ...

    def delete_task(self, task_id: str) -> None:
        """Delete a task.

        :param task_id: Entourage id. Example: ``"1"``
        :return: None
        """
        ...

    def create_project(self, name: str) -> dict[str, Any]:
        """Create a project.

        :param name: Project name. Example: ``"Garden"``
        :return: Created record. Example: ``{"id": "11", "name": "Garden"}``
        """
        ...

    def rename_project(self, project_id: str, name: str) -> dict[str, Any]:
        """Rename a project.

        :param project_id: Entourage id. Example: ``"11"``
        :param name: New name. Example: ``"Yard"``
        :return: Updated record. Example: ``{"id": "11", "name": "Yard"}``
        """
        ...

    def delete_project(self, project_id: str) -> None:
        """Delete a project.

        :param project_id: Entourage id. Example: ``"11"``
        :return: None
        """
        ...

    def create_category(self, name: str, color: str) -> dict[str, Any]:
        """Create a category this sync owns.

        :param name: Category name. Example: ``"Urgent"``
        :param color: Entourage color name. Example: ``"orange"``
        :return: Created record. Example: ``{"id": "20", "name": "Urgent", "color": "orange"}``
        """
        ...

    def rename_category(self, category_id: str, name: str) -> dict[str, Any]:
        """Rename a category this sync created.

        :param category_id: Entourage id. Example: ``"20"``
        :param name: New name. Example: ``"Critical"``
        :return: Updated record. Example: ``{"id": "20", "name": "Critical"}``
        """
        ...

    def set_category_color(self, category_id: str, color: str) -> dict[str, Any]:
        """Set category color.

        :param category_id: Entourage id. Example: ``"20"``
        :param color: Entourage color name. Example: ``"orange"``
        :return: Updated record. Example: ``{"id": "20", "color": "orange"}``
        """
        ...

    def list_events(self) -> list[dict[str, Any]]:
        """Return calendar event records.

        :return: Event dicts. Example: ``[{"id": "1", "subject": "Standup"}]``
        """
        ...

    def create_event(self, properties: dict[str, Any]) -> dict[str, Any]:
        """Create a calendar event.

        :param properties: Event fields. Example: ``{"subject": "Standup"}``
        :return: Created record. Example: ``{"id": "1", "subject": "Standup"}``
        """
        ...

    def update_event(self, event_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Patch a calendar event.

        :param event_id: Entourage id. Example: ``"1"``
        :param properties: Fields to set. Example: ``{"subject": "Standup moved"}``
        :return: Updated record. Example: ``{"id": "1", "subject": "Standup moved"}``
        """
        ...

    def delete_event(self, event_id: str) -> None:
        """Delete a calendar event.

        :param event_id: Entourage id. Example: ``"1"``
        :return: None
        """
        ...

    def get_event_content(self, event_id: str) -> str:
        """Return event notes/content.

        :param event_id: Entourage id. Example: ``"1"``
        :return: Content text. Example: ``"o365pop-uid: evt-standup"``
        """
        ...

    def add_event_attachment(self, event_id: str, name: str, content_type: str, content: bytes) -> dict[str, Any]:
        """Attach a file to an event.

        :param event_id: Entourage id. Example: ``"1"``
        :param name: File name. Example: ``"agenda.pdf"``
        :param content_type: MIME type. Example: ``"application/pdf"``
        :param content: Raw bytes. Example: ``b"%PDF-1.4"``
        :return: Attachment record. Example: ``{"name": "agenda.pdf", "bytes": 32}``
        """
        ...
