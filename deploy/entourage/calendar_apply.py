"""Apply calendar snapshot to Entourage: shared Projects, categories, events."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from deploy.entourage.apply import (
    _category_by_name,
    _project_by_name,
    format_uid,
    parse_iso,
    parse_uid,
)
from deploy.entourage.calendar_snapshot import (
    CalendarSnapshot,
    SnapshotCalendar,
    SnapshotEvent,
)
from deploy.entourage.html_body import html_to_plain, is_html_body
from deploy.entourage.port import EntouragePort
from deploy.entourage.uid_map import UidMap

logger = logging.getLogger(__name__)

ATTENDEES_PREFIX = "o365pop-attendees:"


ATTACHMENT_MAX_BYTES = 5 * 1024 * 1024


def apply_calendar_snapshot(
    snapshot: CalendarSnapshot,
    entourage: EntouragePort,
    uid_map: UidMap,
    attachments_root: Path | None = None,
) -> dict[str, int]:
    """Sync calendar Projects and events from a snapshot.

    :param snapshot: Parsed calendar snapshot. Example: ``parse_calendar_snapshot({...})``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Counts. Example: ``{"created": 1, "updated": 0, "projects_created": 1}``
    """
    logger.info(
        "taskd.apply | entry | calendars=%s events=%s kind=calendar",
        len(snapshot.calendars),
        len(snapshot.events),
    )
    counts = _sync_calendar_projects(snapshot.calendars, entourage, uid_map)
    counts.update(_sync_events(snapshot.events, entourage, uid_map, attachments_root))
    logger.info(
        "taskd.apply | exit | created=%s updated=%s failed=%s kind=calendar",
        counts["created"],
        counts["updated"],
        counts.get("failed", 0),
    )
    return counts


def _sync_calendar_projects(
    calendars: tuple[SnapshotCalendar, ...], entourage: EntouragePort, uid_map: UidMap
) -> dict[str, int]:
    """Index mailbox calendars without creating Projects (Q15 C).

    :param calendars: Snapshot calendars. Example: ``(SnapshotCalendar("cal-work", "Calendar"),)``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Counts. Example: ``{"projects_created": 0, "projects_renamed": 0, "calendar_joins_removed": 0}``
    """
    _ = entourage
    seen: set[str] = set()
    for row in calendars:
        seen.add(row.id)
        uid_map.calendars[row.id] = ""
        logger.info(
            "taskd.apply | branch | calendar_is_not_project=true name=%s graph=%s",
            row.display_name,
            row.id,
        )
    removed = _drop_missing_calendar_ids(seen, uid_map)
    return {
        "projects_created": 0,
        "projects_renamed": 0,
        "calendar_joins_removed": removed,
    }


def _drop_missing_calendar_ids(seen: set[str], uid_map: UidMap) -> int:
    """Drop indexed calendar ids that left the snapshot. Never delete Projects.

    :param seen: Snapshot calendar ids. Example: ``{"cal-work"}``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Removed id count. Example: ``1``
    """
    removed = 0
    for graph_id in list(uid_map.calendars):
        if graph_id in seen:
            continue
        del uid_map.calendars[graph_id]
        removed += 1
        logger.info("taskd.apply | processing | calendar_index_removed graph=%s", graph_id)
    return removed


def _sync_events(
    events: tuple[SnapshotEvent, ...],
    entourage: EntouragePort,
    uid_map: UidMap,
    attachments_root: Path | None,
) -> dict[str, int]:
    """Create or update joined calendar events.

    :param events: Snapshot events. Example: ``(SnapshotEvent(...),)``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Counts. Example: ``{"created": 1, "updated": 0, "deleted": 0, "failed": 0}``
    """
    created = updated = failed = 0
    seen: set[str] = set()
    for row in events:
        seen.add(row.id)
        created_one, updated_one, failed_one = _try_upsert_event(row, entourage, uid_map, attachments_root)
        created += created_one
        updated += updated_one
        failed += failed_one
    deleted = _delete_missing_events(seen, entourage, uid_map)
    return {"created": created, "updated": updated, "deleted": deleted, "failed": failed}


def _try_upsert_event(
    row: SnapshotEvent,
    entourage: EntouragePort,
    uid_map: UidMap,
    attachments_root: Path | None,
) -> tuple[int, int, int]:
    """Create or update one event; log and continue when Entourage rejects it.

    :param row: Snapshot event. Example: ``SnapshotEvent(id="evt-standup", ...)``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :param attachments_root: Attachment dir. Example: ``Path("calendar/attachments")``
    :return: (created, updated, failed). Example: ``(0, 0, 1)``
    """
    try:
        created, updated = _upsert_event(row, entourage, uid_map, attachments_root)
        return created, updated, 0
    except Exception as exc:
        logger.error(
            "taskd.apply | error | uid=%s subject=%s err=%s kind=calendar",
            row.id,
            row.subject,
            exc,
        )
        return 0, 0, 1


def _upsert_event(
    row: SnapshotEvent,
    entourage: EntouragePort,
    uid_map: UidMap,
    attachments_root: Path | None,
) -> tuple[int, int]:
    """Create or update one calendar event unless local is newer.

    :param row: Snapshot event. Example: ``SnapshotEvent(id="evt-standup", ...)``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: (created, updated). Example: ``(1, 0)``
    """
    properties = _event_properties(row, entourage)
    local_id = uid_map.events.get(row.id)
    if local_id is None:
        created = entourage.create_event(properties)
        local_id = str(created["id"])
        uid_map.events[row.id] = local_id
        _apply_attachments(row, local_id, entourage, attachments_root)
        logger.info("taskd.apply | processing | uid=%s kind=calendar", row.id)
        return 1, 0
    # Do not call list_events() here. Live dumps content of every event and
    # times out at 120s; parsed rows have no modification_date so the
    # local-newer skip never fires. Graph wins this hop (same as live).
    entourage.update_event(local_id, properties)
    _apply_attachments(row, local_id, entourage, attachments_root)
    logger.info("taskd.apply | processing | uid=%s kind=calendar", row.id)
    return 0, 1


def _event_properties(row: SnapshotEvent, entourage: EntouragePort) -> dict[str, Any]:
    """Build Entourage event fields from a snapshot row.

    :param row: Snapshot event. Example: ``SnapshotEvent(id="evt-standup", subject="Standup", ...)``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :return: Properties. Example: ``{"subject": "Standup", "content_plain": "o365pop-uid: evt-standup"}``
    """
    project_id = _project_id_from_category(row, entourage)
    props: dict[str, Any] = {
        "subject": row.subject,
        "start": parse_iso(row.start.date_time),
        "end": parse_iso(row.end.date_time),
        "location": row.location,
        "project_id": project_id,
        "categories": _apply_category_names(row.categories, entourage),
        "reminder_minutes": row.reminder_minutes,
        "show_as": row.show_as,
        "sensitivity": row.sensitivity,
        "to_recipients": [],
    }
    props.update(_event_body_fields(row))
    return props


def _project_id_from_category(row: SnapshotEvent, entourage: EntouragePort) -> str | None:
    """Join or create a Project from the event's first category name.

    :param row: Snapshot event. Example: ``SnapshotEvent(..., categories=("Work",))``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :return: Project id or None. Example: ``"12"``
    """
    if not row.categories:
        logger.info("taskd.apply | branch | uncategorized=true uid=%s", row.id)
        return None
    name = row.categories[0]
    existing = _project_by_name(entourage.list_projects(), name)
    if existing is not None:
        logger.info("taskd.apply | branch | project_from_category=true name=%s", name)
        return str(existing["id"])
    project = entourage.create_project(name)
    logger.info("taskd.apply | branch | project_from_category=true name=%s created=true", name)
    return str(project["id"])


def _apply_category_names(names: tuple[str, ...], entourage: EntouragePort) -> list[str]:
    """Return category names that exist locally; never create catalog rows.

    :param names: Graph category names. Example: ``("Urgent",)``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :return: Names to apply. Example: ``["Urgent"]``
    """
    applied: list[str] = []
    for name in names:
        if _category_by_name(entourage.list_categories(), name) is not None:
            applied.append(name)
    return applied


def _event_body_fields(row: SnapshotEvent) -> dict[str, str]:
    """Build Entourage plain notes from Graph content (events are text-only).

    :param row: Snapshot event. Example: ``SnapshotEvent(id="evt-standup", body="<p>Hi</p>", ...)``
    :return: Plain notes. Example: ``{"content_plain": "o365pop-uid: evt-standup\\n\\nHi"}``
    """
    meta_plain = _uid_attendee_lines(row)
    graph_body = _plain_graph_body(row)
    plain = "\n\n".join(part for part in (meta_plain, graph_body) if part)
    return {"content_plain": plain} if plain else {}


def _plain_graph_body(row: SnapshotEvent) -> str:
    """Strip Graph HTML (or mislabeled markup) to readable text.

    :param row: Snapshot event. Example: ``SnapshotEvent(..., body="<p>Hi</p>", body_content_type="html")``
    :return: Plain body. Example: ``"Hi"``
    """
    graph_body = (row.body or "").strip()
    if not graph_body:
        return ""
    graph_type = row.body_content_type or "text"
    if is_html_body(graph_body, graph_type) or is_html_body(graph_body, "text"):
        return html_to_plain(graph_body)
    return graph_body


def _uid_attendee_lines(row: SnapshotEvent) -> str:
    """Uid and attendee metadata as plain text.

    :param row: Snapshot event. Example: ``SnapshotEvent(id="evt-standup", ...)``
    :return: Plain block. Example: ``"o365pop-uid: evt-standup"``
    """
    uid_line = format_uid(row.id)
    plain_lines = [uid_line]
    if row.attendees:
        attendee_bits = []
        for att in row.attendees:
            attendee_bits.append(f"{att.name} <{att.email}> ({att.type})")
        plain_lines.append(f"{ATTENDEES_PREFIX} " + "; ".join(attendee_bits))
    return "\n".join(plain_lines)


def _local_event_newer(event: dict[str, Any], row: SnapshotEvent) -> bool:
    """True when Entourage modification_date is after Graph lastModified.

    :param event: Local event. Example: ``{"modification_date": datetime(...)}``
    :param row: Snapshot event. Example: ``SnapshotEvent(..., last_modified="2026-09-11T15:00:00Z")``
    :return: Comparison. Example: ``True``
    """
    local = event.get("modification_date")
    remote = parse_iso(row.last_modified)
    if not isinstance(local, datetime) or remote is None:
        return False
    if local.tzinfo is None:
        local = local.replace(tzinfo=timezone.utc)
    return local > remote


def _delete_missing_events(seen: set[str], entourage: EntouragePort, uid_map: UidMap) -> int:
    """Delete Entourage events whose Graph id left the snapshot window.

    :param seen: Snapshot event ids. Example: ``{"evt-standup"}``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Deleted count. Example: ``1``
    """
    deleted = 0
    for graph_id, local_id in list(uid_map.events.items()):
        if graph_id in seen:
            continue
        entourage.delete_event(local_id)
        del uid_map.events[graph_id]
        deleted += 1
        logger.info("taskd.apply | processing | event_delete uid=%s", graph_id)
    return deleted


def _event_by_id(events: list[dict[str, Any]], event_id: str) -> dict[str, Any] | None:
    """Find an event record.

    :param events: list_events() copy. Example: ``[{"id": "1"}]``
    :param event_id: Entourage id. Example: ``"1"``
    :return: Record or None. Example: ``{"id": "1", "subject": "Standup"}``
    """
    for row in events:
        if str(row.get("id")) == event_id:
            return row
    return None


def _apply_attachments(
    row: SnapshotEvent,
    local_id: str,
    entourage: EntouragePort,
    attachments_root: Path | None,
) -> None:
    """Copy snapshot attachment files onto the Entourage event.

    :param row: Snapshot event. Example: ``SnapshotEvent(id="evt-standup", ...)``
    :param local_id: Entourage event id. Example: ``"1"``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param attachments_root: ``calendar/attachments``. Example: ``Path("calendar/attachments")``
    :return: None
    """
    if attachments_root is None or not row.attachments:
        return
    for meta in row.attachments:
        path = attachments_root / row.id / meta.name
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size > ATTACHMENT_MAX_BYTES:
            logger.warning(
                "taskd.apply | branch | attachment_skipped=true uid=%s name=%s bytes=%s",
                row.id,
                meta.name,
                size,
            )
            continue
        entourage.add_event_attachment(local_id, meta.name, meta.content_type, path.read_bytes())


def apply_pending_acks(acks_dir: Path, entourage: EntouragePort, uid_map: UidMap) -> int:
    """Stamp Graph uids from LibreELEC ack files onto local events.

    :param acks_dir: ``calendar/acks``. Example: ``Path("calendar/acks")``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Stamped count. Example: ``1``
    """
    if not acks_dir.is_dir():
        return 0
    stamped = 0
    for path in sorted(acks_dir.glob("*.json")):
        local_key = path.stem
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        uid = str(payload.get("uid") or "")
        if not uid:
            continue
        content = entourage.get_event_content(local_key)
        if format_uid(uid) in content:
            path.unlink(missing_ok=True)
            continue
        entourage.update_event(local_key, {"content_plain": _merge_uid(content, uid)})
        uid_map.events[uid] = local_key
        path.unlink(missing_ok=True)
        stamped += 1
        logger.info("taskd.apply | processing | ack_stamped uid=%s localKey=%s", uid, local_key)
    return stamped


def _merge_uid(content: str, uid: str) -> str:
    """Prepend uid line when content lacks one.

    :param content: Existing content. Example: ``""``
    :param uid: Graph event id. Example: ``"evt-new"``
    :return: Updated content. Example: ``"o365pop-uid: evt-new"``
    """
    if parse_uid(content or ""):
        return content
    line = format_uid(uid)
    return f"{line}\n{content}".strip()


def apply_event_categories(snapshot: CalendarSnapshot, entourage: EntouragePort, uid_map: UidMap) -> dict[str, int]:
    """Apply category names on events without mutating the master catalog.

    :param snapshot: Parsed calendar snapshot. Example: ``parse_calendar_snapshot({...})``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Updated count. Example: ``{"events_updated": 1}``
    """
    updated = 0
    for row in snapshot.events:
        local_id = uid_map.events.get(row.id)
        if not local_id:
            continue
        names = []
        for name in row.categories:
            if _category_by_name(entourage.list_categories(), name) is not None:
                names.append(name)
        entourage.update_event(local_id, {"categories": names})
        updated += 1
    return {"events_updated": updated}
