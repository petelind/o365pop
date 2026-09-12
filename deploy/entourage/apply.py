"""Apply a snapshot to Entourage: Projects, categories, then Tasks."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from deploy.entourage.color_map import graph_color_to_entourage
from deploy.entourage.port import EntouragePort
from deploy.entourage.snapshot import Snapshot, SnapshotCategory, SnapshotList, SnapshotTask
from deploy.entourage.uid_map import UidMap

logger = logging.getLogger(__name__)


def apply_snapshot(snapshot: Snapshot, entourage: EntouragePort, uid_map: UidMap) -> dict[str, int]:
    """Sync Projects, categories, and Tasks from a snapshot.

    :param snapshot: Parsed snapshot. Example: ``parse_snapshot({...})``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Counts. Example: ``{"created": 1, "updated": 0, "projects_created": 1}``
    """
    logger.info(
        "taskd.apply | entry | lists=%s categories=%s tasks=%s",
        len(snapshot.lists),
        len(snapshot.categories),
        len(snapshot.tasks),
    )
    counts = _sync_projects(snapshot.lists, entourage, uid_map)
    counts.update(_sync_categories(snapshot.categories, entourage, uid_map))
    counts.update(_sync_tasks(snapshot.tasks, entourage, uid_map))
    logger.info("taskd.apply | exit | created=%s updated=%s", counts["created"], counts["updated"])
    return counts


def backfill_projects(snapshot: Snapshot, entourage: EntouragePort, uid_map: UidMap) -> int:
    """Set ``project list`` on already-joined tasks from their Graph list.

    :param snapshot: Parsed snapshot. Example: ``parse_snapshot({...})``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Assigned count. Example: ``1``
    """
    assigned = 0
    for row in snapshot.tasks:
        local_id = uid_map.tasks.get(row.id)
        project_id = uid_map.lists.get(row.list_id)
        if not local_id or not project_id:
            continue
        try:
            entourage.update_task(local_id, {"project_id": project_id})
        except (RuntimeError, KeyError) as exc:
            logger.warning(
                "taskd.apply | branch | project_backfill_skip uid=%s err=%s",
                row.id,
                type(exc).__name__,
            )
            continue
        assigned += 1
        logger.info("taskd.apply | processing | project_backfill uid=%s", row.id)
    logger.info("taskd.apply | exit | project_backfill=%s", assigned)
    return assigned


def _sync_projects(lists: tuple[SnapshotList, ...], entourage: EntouragePort, uid_map: UidMap) -> dict[str, int]:
    """Create, rename, or delete joined Projects.

    :param lists: Snapshot lists. Example: ``(SnapshotList("list-garden", "Garden"),)``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Counts. Example: ``{"projects_created": 1, "projects_renamed": 0, "projects_deleted": 0}``
    """
    created = renamed = 0
    seen: set[str] = set()
    for row in lists:
        seen.add(row.id)
        created += _ensure_project(row, entourage, uid_map)
        renamed += _rename_if_needed(row, entourage, uid_map)
    deleted = _delete_missing_projects(seen, entourage, uid_map)
    return {"projects_created": created, "projects_renamed": renamed, "projects_deleted": deleted}


def _ensure_project(row: SnapshotList, entourage: EntouragePort, uid_map: UidMap) -> int:
    """Join a same-named Project, or create one when the Graph list is new.

    :param row: Snapshot list. Example: ``SnapshotList("list-garden", "Garden")``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: 1 if created else 0. Example: ``1``
    """
    if row.id in uid_map.lists:
        return 0
    existing = _project_by_name(entourage.list_projects(), row.display_name)
    if existing is not None:
        uid_map.lists[row.id] = str(existing["id"])
        logger.info("taskd.apply | processing | project_join graph=%s name=%s", row.id, row.display_name)
        return 0
    project = entourage.create_project(row.display_name)
    uid_map.lists[row.id] = str(project["id"])
    logger.info("taskd.apply | processing | project_create graph=%s name=%s", row.id, row.display_name)
    return 1


def _rename_if_needed(row: SnapshotList, entourage: EntouragePort, uid_map: UidMap) -> int:
    """Rename the joined Project when displayName changed.

    :param row: Snapshot list. Example: ``SnapshotList("list-garden", "Yard")``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: 1 if renamed else 0. Example: ``1``
    """
    project_id = uid_map.lists.get(row.id)
    if not project_id:
        return 0
    current = _project_by_id(entourage.list_projects(), project_id)
    if current is None or current.get("name") == row.display_name:
        return 0
    entourage.rename_project(project_id, row.display_name)
    logger.info("taskd.apply | processing | project_rename graph=%s name=%s", row.id, row.display_name)
    return 1


def _delete_missing_projects(seen: set[str], entourage: EntouragePort, uid_map: UidMap) -> int:
    """Delete Projects whose Graph list disappeared (TASK1.4 / Q15 C).

    :param seen: Snapshot list ids. Example: ``{"list-work"}``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Deleted count. Example: ``1``
    """
    deleted = 0
    for graph_id, project_id in list(uid_map.lists.items()):
        if graph_id in seen:
            continue
        del uid_map.lists[graph_id]
        entourage.delete_project(project_id)
        deleted += 1
        logger.info("taskd.apply | processing | project_delete graph=%s", graph_id)
    return deleted


def _sync_categories(
    categories: tuple[SnapshotCategory, ...], entourage: EntouragePort, uid_map: UidMap
) -> dict[str, int]:
    """Create or join Outlook categories. Never delete built-ins.

    :param categories: Snapshot categories. Example: ``(SnapshotCategory("cat-red", "Urgent", "preset1"),)``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Counts. Example: ``{"categories_created": 1}``
    """
    created = 0
    for row in categories:
        created += _ensure_category(row, entourage, uid_map)
    return {"categories_created": created}


def _ensure_category(row: SnapshotCategory, entourage: EntouragePort, uid_map: UidMap) -> int:
    """Join by Graph id or name; create when neither exists.

    :param row: Snapshot category. Example: ``SnapshotCategory("cat-red", "Urgent", "preset1")``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: 1 if created else 0. Example: ``1``
    """
    color, _fallback = graph_color_to_entourage(row.color)
    if row.id in uid_map.categories:
        _refresh_joined_category(uid_map.categories[row.id], row.display_name, color, entourage)
        return 0
    existing = _category_by_name(entourage.list_categories(), row.display_name)
    if existing is not None:
        uid_map.categories[row.id] = str(existing["id"])
        if not existing.get("builtin"):
            entourage.set_category_color(str(existing["id"]), color)
        return 0
    created = entourage.create_category(row.display_name, color)
    uid_map.categories[row.id] = str(created["id"])
    logger.info("taskd.apply | processing | category_create name=%s color=%s", row.display_name, color)
    return 1


def _refresh_joined_category(category_id: str, name: str, color: str, entourage: EntouragePort) -> None:
    """Rename and recolor a joined category. Skip color on built-ins.

    :param category_id: Entourage id. Example: ``"20"``
    :param name: Graph displayName. Example: ``"Urgent"``
    :param color: Entourage color. Example: ``"orange"``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :return: None
    """
    current = _category_by_id(entourage.list_categories(), category_id)
    if current is None:
        return
    if current.get("name") != name:
        entourage.rename_category(category_id, name)
    if not current.get("builtin") and current.get("color") != color:
        entourage.set_category_color(category_id, color)


def _category_by_name(categories: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    """Find a category by display name.

    :param categories: list_categories() copy. Example: ``[{"name": "Urgent"}]``
    :param name: Display name. Example: ``"Urgent"``
    :return: Record or None. Example: ``{"id": "20", "name": "Urgent"}``
    """
    for row in categories:
        if row.get("name") == name:
            return row
    return None


def _category_by_id(categories: list[dict[str, Any]], category_id: str) -> dict[str, Any] | None:
    """Find a category by Entourage id.

    :param categories: list_categories() copy. Example: ``[{"id": "20"}]``
    :param category_id: Entourage id. Example: ``"20"``
    :return: Record or None. Example: ``{"id": "20", "name": "Urgent"}``
    """
    for row in categories:
        if str(row.get("id")) == category_id:
            return row
    return None


def _project_by_name(projects: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    """Find a project by display name.

    :param projects: list_projects() copy. Example: ``[{"name": "Garden"}]``
    :param name: Display name. Example: ``"Garden"``
    :return: Record or None. Example: ``{"id": "11", "name": "Garden"}``
    """
    for row in projects:
        if row.get("name") == name:
            return row
    return None


def _project_by_id(projects: list[dict[str, Any]], project_id: str) -> dict[str, Any] | None:
    """Find a project record.

    :param projects: list_projects() copy. Example: ``[{"id": "11", "name": "Garden"}]``
    :param project_id: Entourage id. Example: ``"11"``
    :return: Record or None. Example: ``{"id": "11", "name": "Garden"}``
    """
    for row in projects:
        if str(row.get("id")) == project_id:
            return row
    return None


UID_PREFIX = "o365pop-uid:"


def format_uid(graph_id: str) -> str:
    """Build the join line stored in task content.

    :param graph_id: Graph task id. Example: ``"task-q3"``
    :return: Content line. Example: ``"o365pop-uid: task-q3"``
    """
    return f"{UID_PREFIX} {graph_id}"


def parse_uid(content: str) -> str | None:
    """Extract Graph id from Entourage content (plain or HTML).

    :param content: Task or event notes. Example: ``"o365pop-uid: task-q3\\n"``
    :return: Graph id or None. Example: ``"task-q3"``
    """
    text = content or ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(UID_PREFIX):
            uid = stripped.split(":", 1)[1].strip()
            return uid or None
    marker = UID_PREFIX
    idx = text.find(marker)
    if idx < 0:
        return None
    rest = text[idx + len(marker) :].lstrip()
    if not rest:
        return None
    token = rest.split("<", 1)[0].split(None, 1)[0].strip()
    return token or None


def parse_iso(value: str | None) -> datetime | None:
    """Parse an ISO stamp to aware UTC datetime.

    :param value: ISO string. Example: ``"2026-09-12T21:00:00Z"``
    :return: Datetime or None. Example: ``datetime(2026, 9, 12, 21, 0, tzinfo=timezone.utc)``
    """
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _sync_tasks(tasks: tuple[SnapshotTask, ...], entourage: EntouragePort, uid_map: UidMap) -> dict[str, int]:
    """Create or update joined tasks; delete when Graph dropped them.

    :param tasks: Snapshot tasks. Example: ``(SnapshotTask(id="task-q3", ...),)``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Counts. Example: ``{"created": 1, "updated": 0, "deleted": 0}``
    """
    created = updated = 0
    seen: set[str] = set()
    for row in tasks:
        seen.add(row.id)
        created_one, updated_one = _upsert_task(row, entourage, uid_map)
        created += created_one
        updated += updated_one
    deleted = _delete_missing_tasks(seen, entourage, uid_map)
    return {"created": created, "updated": updated, "deleted": deleted}


def _upsert_task(row: SnapshotTask, entourage: EntouragePort, uid_map: UidMap) -> tuple[int, int]:
    """Create or update one task unless the local copy is newer.

    :param row: Snapshot task. Example: ``SnapshotTask(id="task-q3", title="File the Q3 report", ...)``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: (created, updated). Example: ``(1, 0)``
    """
    properties = _task_properties(row, uid_map)
    local_id = uid_map.tasks.get(row.id)
    if local_id is None:
        created = entourage.create_task(properties)
        uid_map.tasks[row.id] = str(created["id"])
        logger.info("taskd.apply | processing | uid=%s", row.id)
        return 1, 0
    current = _task_by_id(entourage.list_tasks(), local_id)
    if current is not None and _local_newer(current, row):
        logger.info("taskd.apply | branch | uid=%s skipped_local_newer=true", row.id)
        return 0, 0
    entourage.update_task(local_id, properties)
    logger.info("taskd.apply | processing | uid=%s", row.id)
    return 0, 1


def _task_properties(row: SnapshotTask, uid_map: UidMap) -> dict[str, Any]:
    """Build Entourage task fields from a snapshot row.

    :param row: Snapshot task. Example: ``SnapshotTask(id="task-q3", title="File the Q3 report", ...)``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Properties. Example: ``{"name": "File the Q3 report", "content": "o365pop-uid: task-q3"}``
    """
    return {
        "name": row.title,
        "due": parse_iso(row.due_datetime),
        "content": format_uid(row.id),
        "completed": row.status == "completed",
        "project_id": uid_map.lists.get(row.list_id),
        "categories": list(row.categories),
    }


def _local_newer(task: dict[str, Any], row: SnapshotTask) -> bool:
    """True when Entourage modification_date is after Graph lastModified.

    :param task: Local task. Example: ``{"modification_date": datetime(2026, 9, 11, 16, tzinfo=timezone.utc)}``
    :param row: Snapshot task. Example: ``SnapshotTask(..., last_modified="2026-09-11T15:00:00Z")``
    :return: Comparison. Example: ``True``
    """
    local = task.get("modification_date")
    remote = parse_iso(row.last_modified)
    if not isinstance(local, datetime) or remote is None:
        return False
    if local.tzinfo is None:
        local = local.replace(tzinfo=timezone.utc)
    return local > remote


def _delete_missing_tasks(seen: set[str], entourage: EntouragePort, uid_map: UidMap) -> int:
    """Delete Entourage tasks whose Graph id left the snapshot.

    :param seen: Snapshot task ids. Example: ``{"task-q3"}``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Deleted count. Example: ``1``
    """
    deleted = 0
    for graph_id, local_id in list(uid_map.tasks.items()):
        if graph_id in seen:
            continue
        entourage.delete_task(local_id)
        del uid_map.tasks[graph_id]
        deleted += 1
        logger.info("taskd.apply | processing | task_delete uid=%s", graph_id)
    return deleted


def _task_by_id(tasks: list[dict[str, Any]], task_id: str) -> dict[str, Any] | None:
    """Find a task record.

    :param tasks: list_tasks() copy. Example: ``[{"id": "1"}]``
    :param task_id: Entourage id. Example: ``"1"``
    :return: Record or None. Example: ``{"id": "1", "name": "File the Q3 report"}``
    """
    for row in tasks:
        if str(row.get("id")) == task_id:
            return row
    return None
