"""Parse LibreELEC ``tasks/snapshot.json`` (stdlib only)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class SnapshotError(ValueError):
    """Raised when a snapshot object is missing a required id."""


@dataclass(frozen=True)
class SnapshotList:
    """One To Do list row.

    :param id: Graph list id. Example: ``"list-work"``
    :param display_name: List title. Example: ``"Work"``
    """

    id: str
    display_name: str


@dataclass(frozen=True)
class SnapshotCategory:
    """One Outlook masterCategory row.

    :param id: Graph category id. Example: ``"cat-red"``
    :param display_name: Category name. Example: ``"Urgent"``
    :param color: Graph preset. Example: ``"preset1"``
    """

    id: str
    display_name: str
    color: str


@dataclass(frozen=True)
class SnapshotTask:
    """One todoTask row.

    :param id: Graph task id. Example: ``"task-q3"``
    :param list_id: Parent list id. Example: ``"list-work"``
    :param title: Task title. Example: ``"File the Q3 report"``
    :param due_datetime: Due instant or None. Example: ``"2026-09-12T21:00:00Z"``
    :param status: Graph status. Example: ``"notStarted"``
    :param categories: Category names. Example: ``("Work",)``
    :param last_modified: Graph stamp or None. Example: ``"2026-09-11T15:00:00Z"``
    """

    id: str
    list_id: str
    title: str
    due_datetime: str | None
    status: str
    categories: tuple[str, ...]
    last_modified: str | None


@dataclass(frozen=True)
class Snapshot:
    """Validated snapshot document.

    :param generated_at: Publisher stamp. Example: ``"2026-09-11T16:00:00Z"``
    :param lists: To Do lists. Example: ``(SnapshotList("list-work", "Work"),)``
    :param categories: Outlook categories. Example: ``()``
    :param tasks: Tasks. Example: ``()``
    """

    generated_at: str
    lists: tuple[SnapshotList, ...]
    categories: tuple[SnapshotCategory, ...]
    tasks: tuple[SnapshotTask, ...]


def parse_snapshot(payload: dict[str, Any]) -> Snapshot:
    """Validate a snapshot dict and return typed rows.

    :param payload: Decoded JSON object. Example: ``{"lists": [{"id": "list-work"}]}``
    :return: Snapshot. Example: ``Snapshot(generated_at="", lists=(...), ...)``
    :raises SnapshotError: if a list, category, or task is missing ``id``
    :raises TypeError: if payload is not a dict
    """
    logger.info(
        "taskd.snapshot.parse | entry | keys=%s", sorted(payload.keys()) if isinstance(payload, dict) else type(payload)
    )
    if not isinstance(payload, dict):
        raise TypeError("snapshot payload must be a dict")
    snapshot = Snapshot(
        generated_at=str(payload.get("generated_at") or ""),
        lists=tuple(_parse_list(row) for row in _as_rows(payload.get("lists"))),
        categories=tuple(_parse_category(row) for row in _as_rows(payload.get("categories"))),
        tasks=tuple(_parse_task(row) for row in _as_rows(payload.get("tasks"))),
    )
    logger.info(
        "taskd.snapshot.parse | exit | lists=%s categories=%s tasks=%s",
        len(snapshot.lists),
        len(snapshot.categories),
        len(snapshot.tasks),
    )
    return snapshot


def _as_rows(value: Any) -> list[dict[str, Any]]:
    """Coerce a JSON array of objects.

    :param value: Raw lists/categories/tasks value. Example: ``[{"id": "list-work"}]``
    :return: Object rows. Example: ``[{"id": "list-work"}]``
    :raises SnapshotError: if an item is not an object
    """
    if value is None:
        return []
    if not isinstance(value, list):
        raise SnapshotError("snapshot collection must be a list")
    rows: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise SnapshotError("snapshot row must be an object")
        rows.append(item)
    return rows


def _require_id(row: dict[str, Any], kind: str) -> str:
    """Return a non-empty id or raise.

    :param row: Snapshot object. Example: ``{"id": "task-q3"}``
    :param kind: Row kind for the error. Example: ``"task"``
    :return: Id string. Example: ``"task-q3"``
    :raises SnapshotError: if ``id`` is missing or blank
    """
    raw = row.get("id")
    if raw is None or str(raw).strip() == "":
        raise SnapshotError(f"{kind} missing id")
    return str(raw)


def _parse_list(row: dict[str, Any]) -> SnapshotList:
    """Build one list row.

    :param row: Raw list. Example: ``{"id": "list-work", "displayName": "Work"}``
    :return: SnapshotList. Example: ``SnapshotList(id="list-work", display_name="Work")``
    :raises SnapshotError: if id is missing
    """
    return SnapshotList(
        id=_require_id(row, "list"), display_name=str(row.get("displayName") or row.get("display_name") or "")
    )


def _parse_category(row: dict[str, Any]) -> SnapshotCategory:
    """Build one category row.

    :param row: Raw category. Example: ``{"id": "cat-red", "displayName": "Urgent", "color": "preset1"}``
    :return: SnapshotCategory. Example: ``SnapshotCategory(id="cat-red", display_name="Urgent", color="preset1")``
    :raises SnapshotError: if id is missing
    """
    return SnapshotCategory(
        id=_require_id(row, "category"),
        display_name=str(row.get("displayName") or row.get("display_name") or ""),
        color=str(row.get("color") or "none"),
    )


def _parse_task(row: dict[str, Any]) -> SnapshotTask:
    """Build one task row.

    :param row: Raw task. Example: ``{"id": "task-q3", "listId": "list-work", "title": "File the Q3 report"}``
    :return: SnapshotTask. Example: ``SnapshotTask(id="task-q3", list_id="list-work", ...)``
    :raises SnapshotError: if id is missing
    """
    categories = row.get("categories") or []
    names = tuple(str(item) for item in categories) if isinstance(categories, list) else ()
    return SnapshotTask(
        id=_require_id(row, "task"),
        list_id=str(row.get("listId") or row.get("list_id") or ""),
        title=str(row.get("title") or ""),
        due_datetime=_due_string(row.get("dueDateTime") or row.get("due_datetime")),
        status=str(row.get("status") or "notStarted"),
        categories=names,
        last_modified=_optional_str(row.get("lastModifiedDateTime") or row.get("last_modified")),
    )


def _optional_str(value: Any) -> str | None:
    """Blank-safe optional string.

    :param value: Raw field. Example: ``"2026-09-11T15:00:00Z"``
    :return: String or None. Example: ``"2026-09-11T15:00:00Z"``
    """
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _due_string(value: Any) -> str | None:
    """Normalize Graph dueDateTime object or ISO string.

    :param value: Raw due. Example: ``{"dateTime": "2026-09-12T21:00:00", "timeZone": "UTC"}``
    :return: ISO-ish string or None. Example: ``"2026-09-12T21:00:00Z"``
    """
    if value is None or value == "":
        return None
    if isinstance(value, dict):
        raw = str(value.get("dateTime") or "").strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            return raw
        if "." in raw:
            raw = raw.split(".", 1)[0]
        return f"{raw}Z"
    return str(value)
