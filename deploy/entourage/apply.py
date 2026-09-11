"""Apply a snapshot to Entourage: lists→Projects first (TASK1.2–1.4)."""

from __future__ import annotations

import logging
from typing import Any

from deploy.entourage.port import EntouragePort
from deploy.entourage.snapshot import Snapshot, SnapshotList
from deploy.entourage.uid_map import UidMap

logger = logging.getLogger(__name__)


def apply_snapshot(snapshot: Snapshot, entourage: EntouragePort, uid_map: UidMap) -> dict[str, int]:
    """Sync Projects from To Do lists. Categories and tasks land in later slices.

    :param snapshot: Parsed snapshot. Example: ``parse_snapshot({...})``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Counts. Example: ``{"projects_created": 1, "projects_renamed": 0, "projects_deleted": 0}``
    """
    logger.info("taskd.apply | entry | lists=%s", len(snapshot.lists))
    counts = _sync_projects(snapshot.lists, entourage, uid_map)
    logger.info(
        "taskd.apply | exit | created=%s updated=%s deleted=%s",
        counts["projects_created"],
        counts["projects_renamed"],
        counts["projects_deleted"],
    )
    return counts


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
    """Create a Project when the Graph list is not joined.

    :param row: Snapshot list. Example: ``SnapshotList("list-garden", "Garden")``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: 1 if created else 0. Example: ``1``
    """
    if row.id in uid_map.lists:
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
    """Delete Projects whose Graph list disappeared.

    :param seen: Snapshot list ids. Example: ``{"list-work"}``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Deleted count. Example: ``1``
    """
    deleted = 0
    for graph_id, project_id in list(uid_map.lists.items()):
        if graph_id in seen:
            continue
        entourage.delete_project(project_id)
        del uid_map.lists[graph_id]
        deleted += 1
        logger.info("taskd.apply | processing | project_delete graph=%s", graph_id)
    return deleted


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
