"""In-memory EntouragePort for TASK tests (FileGraphAdapter analog; no mocks)."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

BUILTIN_CATEGORIES = (
    ("Family", "red"),
    ("Friends", "orange"),
    ("Holiday", "green"),
    ("Junk", "gray"),
    ("Personal", "purple"),
    ("Recreation", "blue"),
    ("Travel", "steel"),
    ("Work", "blue"),
)


class FakeEntourage:
    """Real in-memory Entourage surface. Tests mutate this object, not unittest.mock."""

    def __init__(self) -> None:
        self._next_id = 1
        self._tasks: list[dict[str, Any]] = []
        self._projects: list[dict[str, Any]] = []
        self._categories: list[dict[str, Any]] = [
            {
                "id": f"builtin-{name.lower()}",
                "name": name,
                "color": color,
                "builtin": True,
            }
            for name, color in BUILTIN_CATEGORIES
        ]

    def list_tasks(self) -> list[dict[str, Any]]:
        """Copy of tasks.

        :return: Task dicts. Example: ``[{"id": "1", "name": "File the Q3 report"}]``
        """
        return [copy.deepcopy(row) for row in self._tasks]

    def list_projects(self) -> list[dict[str, Any]]:
        """Copy of projects.

        :return: Project dicts. Example: ``[{"id": "10", "name": "Work"}]``
        """
        return [copy.deepcopy(row) for row in self._projects]

    def list_categories(self) -> list[dict[str, Any]]:
        """Copy of categories.

        :return: Category dicts. Example: ``[{"id": "builtin-work", "name": "Work"}]``
        """
        return [copy.deepcopy(row) for row in self._categories]

    def create_task(self, properties: dict[str, Any]) -> dict[str, Any]:
        """Append a task.

        :param properties: Task fields. Example: ``{"name": "File the Q3 report"}``
        :return: Created record. Example: ``{"id": "1", "name": "File the Q3 report"}``
        """
        row = self._new_row(properties)
        row.setdefault("completed", False)
        row.setdefault("content", "")
        row.setdefault("categories", [])
        row.setdefault("project_id", None)
        row.setdefault("due", None)
        self._tasks.append(row)
        return copy.deepcopy(row)

    def update_task(self, task_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Patch a task in place.

        :param task_id: Entourage id. Example: ``"1"``
        :param properties: Fields to set. Example: ``{"completed": True}``
        :return: Updated record. Example: ``{"id": "1", "completed": True}``
        :raises KeyError: if the task is missing
        """
        row = self._find(self._tasks, task_id)
        row.update(properties)
        row["modification_date"] = _now()
        return copy.deepcopy(row)

    def delete_task(self, task_id: str) -> None:
        """Remove a task.

        :param task_id: Entourage id. Example: ``"1"``
        :return: None
        """
        self._tasks = [row for row in self._tasks if row["id"] != task_id]

    def create_project(self, name: str) -> dict[str, Any]:
        """Append a project.

        :param name: Project name. Example: ``"Garden"``
        :return: Created record. Example: ``{"id": "2", "name": "Garden"}``
        """
        row = self._new_row({"name": name})
        self._projects.append(row)
        return copy.deepcopy(row)

    def rename_project(self, project_id: str, name: str) -> dict[str, Any]:
        """Rename a project.

        :param project_id: Entourage id. Example: ``"2"``
        :param name: New name. Example: ``"Yard"``
        :return: Updated record. Example: ``{"id": "2", "name": "Yard"}``
        :raises KeyError: if the project is missing
        """
        row = self._find(self._projects, project_id)
        row["name"] = name
        row["modification_date"] = _now()
        return copy.deepcopy(row)

    def delete_project(self, project_id: str) -> None:
        """Remove a project.

        :param project_id: Entourage id. Example: ``"2"``
        :return: None
        """
        self._projects = [row for row in self._projects if row["id"] != project_id]

    def create_category(self, name: str, color: str) -> dict[str, Any]:
        """Append a sync-owned category.

        :param name: Category name. Example: ``"Urgent"``
        :param color: Entourage color. Example: ``"orange"``
        :return: Created record. Example: ``{"id": "3", "name": "Urgent", "color": "orange"}``
        """
        row = self._new_row({"name": name, "color": color, "builtin": False})
        self._categories.append(row)
        return copy.deepcopy(row)

    def rename_category(self, category_id: str, name: str) -> dict[str, Any]:
        """Rename a category.

        :param category_id: Entourage id. Example: ``"3"``
        :param name: New name. Example: ``"Critical"``
        :return: Updated record. Example: ``{"id": "3", "name": "Critical"}``
        :raises KeyError: if the category is missing
        """
        row = self._find(self._categories, category_id)
        row["name"] = name
        return copy.deepcopy(row)

    def set_category_color(self, category_id: str, color: str) -> dict[str, Any]:
        """Set category color.

        :param category_id: Entourage id. Example: ``"3"``
        :param color: Entourage color. Example: ``"orange"``
        :return: Updated record. Example: ``{"id": "3", "color": "orange"}``
        :raises KeyError: if the category is missing
        """
        row = self._find(self._categories, category_id)
        row["color"] = color
        return copy.deepcopy(row)

    def _new_row(self, properties: dict[str, Any]) -> dict[str, Any]:
        """Allocate an id and stamp modification_date.

        :param properties: Initial fields. Example: ``{"name": "Garden"}``
        :return: Stored row. Example: ``{"id": "4", "name": "Garden"}``
        """
        row = dict(properties)
        row["id"] = str(self._next_id)
        self._next_id += 1
        row["modification_date"] = _now()
        return row

    def _find(self, rows: list[dict[str, Any]], row_id: str) -> dict[str, Any]:
        """Return the live row or raise.

        :param rows: Store. Example: ``self._tasks``
        :param row_id: Entourage id. Example: ``"1"``
        :return: Live dict. Example: ``{"id": "1"}``
        :raises KeyError: if missing
        """
        for row in rows:
            if row["id"] == row_id:
                return row
        raise KeyError(row_id)


def _now() -> datetime:
    """UTC now for modification stamps.

    :return: Aware datetime. Example: ``datetime(2026, 9, 11, 16, 0, tzinfo=timezone.utc)``
    """
    return datetime.now(timezone.utc)
