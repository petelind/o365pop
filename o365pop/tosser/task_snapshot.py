"""Publish To Do snapshot.json for Mac taskd (LibreELEC side)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from o365pop.graph.port import GraphPort

logger = logging.getLogger(__name__)


def publish(graph: GraphPort, dest: Path) -> dict[str, Any]:
    """Write lists, categories, and tasks atomically to dest.

    :param graph: GraphPort. Example: ``FileGraphAdapter(case_dir)``
    :param dest: snapshot.json path. Example: ``Path("var/tasks/snapshot.json")``
    :return: Counts. Example: ``{"lists": 1, "tasks": 1, "bytes": 240}``
    """
    lists, categories, tasks = _collect(graph)
    logger.info("tosser.task_snapshot.publish | entry | lists=%s tasks=%s", len(lists), len(tasks))
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lists": lists,
        "categories": categories,
        "tasks": tasks,
    }
    body = json.dumps(payload, indent=2)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.parent / f"{dest.name}.tmp"
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(dest)
    size = dest.stat().st_size
    logger.info("tosser.task_snapshot.publish | exit | path=%s bytes=%s", dest, size)
    return {"lists": len(lists), "tasks": len(tasks), "bytes": size}


def _collect(graph: GraphPort) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Pull lists, categories, and flattened tasks.

    :param graph: GraphPort. Example: ``FileGraphAdapter(case_dir)``
    :return: lists, categories, tasks. Example: ``([{...}], [], [{...}])``
    """
    lists = [_public_list(row) for row in graph.list_todo_lists()]
    categories = [_public_category(row) for row in graph.list_master_categories()]
    tasks: list[dict[str, Any]] = []
    for row in lists:
        list_id = str(row["id"])
        for task in graph.list_todo_tasks(list_id):
            tasks.append(_public_task(task, list_id))
    return lists, categories, tasks


def _public_list(row: dict[str, Any]) -> dict[str, Any]:
    """Keep snapshot list fields.

    :param row: Graph list. Example: ``{"id": "list-work", "displayName": "Work"}``
    :return: Snapshot list. Example: ``{"id": "list-work", "displayName": "Work"}``
    """
    return {"id": str(row.get("id") or ""), "displayName": str(row.get("displayName") or "")}


def _public_category(row: dict[str, Any]) -> dict[str, Any]:
    """Keep snapshot category fields.

    :param row: Graph category. Example: ``{"id": "cat-red", "color": "preset1"}``
    :return: Snapshot category. Example: ``{"id": "cat-red", "displayName": "Urgent", "color": "preset1"}``
    """
    return {
        "id": str(row.get("id") or ""),
        "displayName": str(row.get("displayName") or ""),
        "color": str(row.get("color") or "none"),
    }


def _public_task(row: dict[str, Any], list_id: str) -> dict[str, Any]:
    """Flatten one todoTask onto the snapshot contract.

    :param row: Graph task. Example: ``{"id": "task-q3", "title": "File the Q3 report"}``
    :param list_id: Parent list. Example: ``"list-work"``
    :return: Snapshot task. Example: ``{"id": "task-q3", "listId": "list-work"}``
    """
    categories = row.get("categories") or []
    names = [str(item) for item in categories] if isinstance(categories, list) else []
    return {
        "id": str(row.get("id") or ""),
        "listId": list_id,
        "title": str(row.get("title") or ""),
        "dueDateTime": _due_iso(row.get("dueDateTime")),
        "status": str(row.get("status") or "notStarted"),
        "categories": names,
        "lastModifiedDateTime": str(row.get("lastModifiedDateTime") or ""),
    }


def _due_iso(value: Any) -> str | None:
    """Normalize Graph dueDateTime to an ISO Z string.

    :param value: Graph due. Example: ``{"dateTime": "2026-09-12T21:00:00.0000000", "timeZone": "UTC"}``
    :return: ISO string or None. Example: ``"2026-09-12T21:00:00Z"``
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
