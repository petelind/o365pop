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


RECEIPT_MAX_ATTEMPTS = 3


def apply_receipts(graph: GraphPort, receipts_dir: Path) -> dict[str, int]:
    """PATCH/DELETE Graph from Mac receipt JSON. Moves files to sent/ or failed/.

    :param graph: GraphPort. Example: ``FileGraphAdapter(case_dir)``
    :param receipts_dir: ``tasks/receipts``. Example: ``Path("var/tasks/receipts")``
    :return: Counts. Example: ``{"patched": 1, "deleted": 0}``
    """
    new_dir = receipts_dir / "new"
    sent_dir = receipts_dir / "sent"
    failed_dir = receipts_dir / "failed"
    sent_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)
    patched = deleted = 0
    if not new_dir.is_dir():
        return {"patched": 0, "deleted": 0}
    for path in sorted(new_dir.glob("*.json")):
        patched_one, deleted_one = _apply_one_receipt(graph, path, sent_dir, failed_dir)
        patched += patched_one
        deleted += deleted_one
    return {"patched": patched, "deleted": deleted}


def _apply_one_receipt(graph: GraphPort, path: Path, sent_dir: Path, failed_dir: Path) -> tuple[int, int]:
    """Apply one receipt file.

    :param graph: GraphPort. Example: ``FileGraphAdapter(case_dir)``
    :param path: Receipt JSON. Example: ``Path("receipts/new/task-q3.json")``
    :param sent_dir: Success dir. Example: ``Path("receipts/sent")``
    :param failed_dir: Failure dir. Example: ``Path("receipts/failed")``
    :return: (patched, deleted). Example: ``(1, 0)``
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        patched, deleted = _dispatch_receipt(graph, payload)
        path.replace(sent_dir / path.name)
        return patched, deleted
    except Exception as exc:
        logger.error("tosser.task_snapshot.apply_receipts | error | path=%s err=%s", path.name, type(exc).__name__)
        _bump_or_fail(path, failed_dir)
        return 0, 0


def _dispatch_receipt(graph: GraphPort, payload: dict[str, Any]) -> tuple[int, int]:
    """PATCH or DELETE one Graph task.

    :param graph: GraphPort. Example: ``FileGraphAdapter(case_dir)``
    :param payload: Receipt. Example: ``{"uid": "task-q3", "listId": "list-work", "status": "completed"}``
    :return: (patched, deleted). Example: ``(1, 0)``
    """
    list_id = str(payload["listId"])
    task_id = str(payload["uid"])
    if payload.get("deleted"):
        graph.delete_todo_task(list_id, task_id)
        return 0, 1
    graph.patch_todo_task(list_id, task_id, _patch_body(payload))
    return 1, 0


def _patch_body(payload: dict[str, Any]) -> dict[str, Any]:
    """Graph PATCH body from a receipt.

    :param payload: Receipt. Example: ``{"status": "completed", "title": "File the Q3 report"}``
    :return: Patch object. Example: ``{"status": "completed"}``
    """
    body: dict[str, Any] = {"status": str(payload.get("status") or "notStarted")}
    if payload.get("title"):
        body["title"] = str(payload["title"])
    if payload.get("dueDateTime"):
        body["dueDateTime"] = {"dateTime": str(payload["dueDateTime"]).replace("Z", ""), "timeZone": "UTC"}
    return body


def _bump_or_fail(path: Path, failed_dir: Path) -> None:
    """Increment attempts or move to failed/.

    :param path: Receipt still in new/. Example: ``Path("receipts/new/task-q3.json")``
    :param failed_dir: failed/. Example: ``Path("receipts/failed")``
    :return: None
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        path.replace(failed_dir / path.name)
        return
    if not isinstance(payload, dict):
        path.replace(failed_dir / path.name)
        return
    attempts = int(payload.get("attempts") or 0) + 1
    payload["attempts"] = attempts
    if attempts >= RECEIPT_MAX_ATTEMPTS:
        path.replace(failed_dir / path.name)
        return
    path.write_text(json.dumps(payload), encoding="utf-8")


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
