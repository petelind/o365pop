"""Queue Entourage → Graph receipts. Untagged local tasks stay local (TASK1.7)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from deploy.entourage.apply import parse_iso, parse_uid
from deploy.entourage.port import EntouragePort
from deploy.entourage.snapshot import Snapshot, SnapshotTask
from deploy.entourage.uid_map import UidMap

logger = logging.getLogger(__name__)


def queue_receipts(
    entourage: EntouragePort,
    uid_map: UidMap,
    snapshot: Snapshot,
    receipts_dir: Path,
) -> int:
    """Write receipt JSON for joined tasks that differ from the snapshot.

    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :param snapshot: Last pulled snapshot. Example: ``parse_snapshot({...})``
    :param receipts_dir: ``tasks/receipts``. Example: ``Path("var/tasks/receipts")``
    :return: Queued count. Example: ``1``
    """
    new_dir = receipts_dir / "new"
    new_dir.mkdir(parents=True, exist_ok=True)
    by_id = {row.id: row for row in snapshot.tasks}
    queued = 0
    live_uids: set[str] = set()
    for task in entourage.list_tasks():
        queued += _queue_live_task(task, by_id, uid_map, new_dir, live_uids)
    queued += _queue_deleted_tasks(live_uids, by_id, uid_map, new_dir)
    return queued


def _queue_live_task(
    task: dict[str, Any],
    by_id: dict[str, SnapshotTask],
    uid_map: UidMap,
    new_dir: Path,
    live_uids: set[str],
) -> int:
    """Queue one live task or skip untagged/local-equal rows.

    :param task: Entourage task. Example: ``{"name": "File the Q3 report", "completed": True}``
    :param by_id: Snapshot tasks. Example: ``{"task-q3": SnapshotTask(...)}``
    :param uid_map: Joins. Example: ``UidMap()``
    :param new_dir: receipts/new. Example: ``Path("receipts/new")``
    :param live_uids: Seen Graph ids. Example: ``{"task-q3"}``
    :return: 1 if queued else 0. Example: ``1``
    """
    uid = parse_uid(str(task.get("content") or ""))
    if not uid:
        logger.info("taskd.apply | branch | skipped_local=1")
        return 0
    live_uids.add(uid)
    snap = by_id.get(uid)
    if snap is None or not _differs(task, snap):
        return 0
    list_id = snap.list_id or _list_id_for_task(uid, uid_map)
    _write_receipt(new_dir, _receipt_payload(uid, list_id, task, deleted=False))
    return 1


def _queue_deleted_tasks(
    live_uids: set[str],
    by_id: dict[str, SnapshotTask],
    uid_map: UidMap,
    new_dir: Path,
) -> int:
    """Queue DELETE receipts when a joined Entourage task disappeared.

    :param live_uids: Graph ids still in Entourage. Example: ``{"task-q3"}``
    :param by_id: Snapshot tasks. Example: ``{"task-q3": SnapshotTask(...)}``
    :param uid_map: Joins. Example: ``UidMap()``
    :param new_dir: receipts/new. Example: ``Path("receipts/new")``
    :return: Queued deletes. Example: ``1``
    """
    queued = 0
    for uid in list(uid_map.tasks):
        if uid in live_uids:
            continue
        snap = by_id.get(uid)
        list_id = snap.list_id if snap is not None else _list_id_for_task(uid, uid_map)
        payload = {
            "uid": uid,
            "listId": list_id,
            "deleted": True,
            "status": "deleted",
            "modifiedAt": _now_iso(),
        }
        _write_receipt(new_dir, payload)
        queued += 1
    return queued


def _differs(task: dict[str, Any], snap: SnapshotTask) -> bool:
    """True when title, due, or completed disagree with Graph.

    :param task: Entourage task. Example: ``{"completed": True, "name": "File the Q3 report"}``
    :param snap: Snapshot row. Example: ``SnapshotTask(..., status="notStarted")``
    :return: Differs. Example: ``True``
    """
    if bool(task.get("completed")) != (snap.status == "completed"):
        return True
    if str(task.get("name") or "") != snap.title:
        return True
    return _due_iso(task.get("due")) != (snap.due_datetime or None)


def _receipt_payload(uid: str, list_id: str, task: dict[str, Any], *, deleted: bool) -> dict[str, Any]:
    """Build one receipt object.

    :param uid: Graph task id. Example: ``"task-q3"``
    :param list_id: Graph list id. Example: ``"list-work"``
    :param task: Entourage task. Example: ``{"name": "File the Q3 report", "completed": True}``
    :param deleted: Delete flag. Example: ``False``
    :return: Receipt dict. Example: ``{"uid": "task-q3", "status": "completed"}``
    """
    status = "completed" if task.get("completed") else "notStarted"
    return {
        "uid": uid,
        "listId": list_id,
        "title": str(task.get("name") or ""),
        "dueDateTime": _due_iso(task.get("due")),
        "status": status,
        "deleted": deleted,
        "modifiedAt": _now_iso(),
    }


def _write_receipt(new_dir: Path, payload: dict[str, Any]) -> None:
    """Write receipts/new/{uid}.json and log the beat.

    :param new_dir: receipts/new. Example: ``Path("receipts/new")``
    :param payload: Receipt. Example: ``{"uid": "task-q3", "status": "completed"}``
    :return: None
    """
    path = new_dir / f"{payload['uid']}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    logger.info("taskd.receipts | exit | uid=%s status=%s", payload["uid"], payload.get("status"))


def _list_id_for_task(uid: str, uid_map: UidMap) -> str:
    """Best-effort list id when the snapshot row is already gone.

    :param uid: Graph task id. Example: ``"task-q3"``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: List id or empty. Example: ``"list-work"``
    """
    if uid and len(uid_map.lists) == 1:
        return next(iter(uid_map.lists))
    return ""


def _due_iso(value: Any) -> str | None:
    """Format a datetime or pass through an ISO string.

    :param value: Due field. Example: ``datetime(2026, 9, 12, 21, 0, tzinfo=timezone.utc)``
    :return: ISO Z or None. Example: ``"2026-09-12T21:00:00Z"``
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        stamp = value.astimezone(timezone.utc)
        return stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    parsed = parse_iso(str(value))
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ") if parsed else str(value)


def _now_iso() -> str:
    """UTC now as ISO Z.

    :return: Stamp. Example: ``"2026-09-11T16:10:00Z"``
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
