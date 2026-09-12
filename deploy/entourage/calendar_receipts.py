"""Queue Entourage calendar → Graph receipts (no attendee PATCH)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from deploy.entourage.apply import parse_uid
from deploy.entourage.calendar_snapshot import CalendarSnapshot, SnapshotEvent
from deploy.entourage.port import EntouragePort
from deploy.entourage.uid_map import UidMap

logger = logging.getLogger(__name__)


def queue_calendar_receipts(
    entourage: EntouragePort,
    uid_map: UidMap,
    snapshot: CalendarSnapshot,
    receipts_dir: Path,
) -> int:
    """Write receipt JSON for joined events that differ from the snapshot.

    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :param snapshot: Last pulled calendar snapshot. Example: ``parse_calendar_snapshot({...})``
    :param receipts_dir: ``calendar/receipts``. Example: ``Path("calendar/receipts")``
    :return: Queued count. Example: ``1``
    """
    new_dir = receipts_dir / "new"
    new_dir.mkdir(parents=True, exist_ok=True)
    by_id = {row.id: row for row in snapshot.events}
    queued = 0
    live_uids: set[str] = set()
    for event in entourage.list_events():
        queued += _queue_live_event(event, by_id, uid_map, new_dir, live_uids)
    queued += _queue_create_events(entourage, uid_map, snapshot, new_dir)
    queued += _queue_deleted_events(live_uids, by_id, uid_map, new_dir)
    return queued


def _queue_live_event(
    event: dict[str, Any],
    by_id: dict[str, SnapshotEvent],
    uid_map: UidMap,
    new_dir: Path,
    live_uids: set[str],
) -> int:
    """Queue one joined event PATCH when fields differ.

    :param event: Entourage event. Example: ``{"subject": "Standup moved"}``
    :param by_id: Snapshot events. Example: ``{"evt-standup": SnapshotEvent(...)}``
    :param uid_map: Joins. Example: ``UidMap()``
    :param new_dir: receipts/new. Example: ``Path("receipts/new")``
    :param live_uids: Seen Graph ids. Example: ``{"evt-standup"}``
    :return: 1 if queued else 0. Example: ``1``
    """
    uid = parse_uid(str(event.get("content") or ""))
    if not uid:
        return 0
    live_uids.add(uid)
    snap = by_id.get(uid)
    if snap is None or not _event_differs(event, snap):
        return 0
    calendar_id = snap.calendar_id or _calendar_id_for_event(uid, uid_map)
    payload = _patch_receipt(uid, calendar_id, event)
    _write_receipt(new_dir, payload)
    return 1


def _queue_create_events(entourage: EntouragePort, uid_map: UidMap, snapshot: CalendarSnapshot, new_dir: Path) -> int:
    """Queue POST receipts for untagged local events onto the default calendar.

    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :param uid_map: Joins. Example: ``UidMap()``
    :param snapshot: Last pulled calendar snapshot. Example: ``parse_calendar_snapshot({...})``
    :param new_dir: receipts/new. Example: ``Path("receipts/new")``
    :return: Queued creates. Example: ``1``
    """
    queued = 0
    calendar_id = _default_calendar_id(snapshot, uid_map)
    if not calendar_id:
        return 0
    joined_locals = set(uid_map.events.values())
    for event in entourage.list_events():
        local_id = str(event.get("id") or "")
        if local_id in joined_locals:
            continue
        if parse_uid(str(event.get("content") or "")):
            continue
        payload = _create_receipt(local_id, calendar_id, event)
        _write_receipt(new_dir, payload, filename=f"local-{local_id}.json")
        queued += 1
    return queued


def _default_calendar_id(snapshot: CalendarSnapshot, uid_map: UidMap) -> str:
    """Return the default mailbox calendar id, else the sole indexed calendar.

    :param snapshot: Parsed snapshot. Example: ``parse_calendar_snapshot({...})``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Calendar id or empty. Example: ``"cal-work"``
    """
    for row in snapshot.calendars:
        if row.is_default:
            return row.id
    if snapshot.calendars:
        return snapshot.calendars[0].id
    if len(uid_map.calendars) == 1:
        return next(iter(uid_map.calendars))
    return ""


def _queue_deleted_events(
    live_uids: set[str],
    by_id: dict[str, SnapshotEvent],
    uid_map: UidMap,
    new_dir: Path,
) -> int:
    """Queue DELETE receipts when a joined Entourage event disappeared.

    :param live_uids: Graph ids still in Entourage. Example: ``{"evt-standup"}``
    :param by_id: Snapshot events. Example: ``{"evt-standup": SnapshotEvent(...)}``
    :param uid_map: Joins. Example: ``UidMap()``
    :param new_dir: receipts/new. Example: ``Path("receipts/new")``
    :return: Queued deletes. Example: ``1``
    """
    queued = 0
    for uid in list(uid_map.events):
        if uid in live_uids:
            continue
        payload = {
            "uid": uid,
            "deleted": True,
            "modifiedAt": _now_iso(),
        }
        _write_receipt(new_dir, payload)
        queued += 1
    return queued


def _event_differs(event: dict[str, Any], snap: SnapshotEvent) -> bool:
    """True when editable fields disagree with Graph (attendees excluded).

    :param event: Entourage event. Example: ``{"subject": "Standup moved"}``
    :param snap: Snapshot row. Example: ``SnapshotEvent(..., subject="Standup")``
    :return: Differs. Example: ``True``
    """
    if str(event.get("subject") or "") != snap.subject:
        return True
    if str(event.get("location") or "") != snap.location:
        return True
    if str(event.get("show_as") or "") != snap.show_as:
        return True
    if str(event.get("sensitivity") or "") != snap.sensitivity:
        return True
    if event.get("reminder_minutes") != snap.reminder_minutes:
        return True
    return False


def _patch_receipt(uid: str, calendar_id: str, event: dict[str, Any]) -> dict[str, Any]:
    """Build one PATCH receipt (no attendees field).

    :param uid: Graph event id. Example: ``"evt-standup"``
    :param calendar_id: Graph calendar id. Example: ``"cal-work"``
    :param event: Entourage event. Example: ``{"subject": "Standup moved"}``
    :return: Receipt dict. Example: ``{"uid": "evt-standup", "subject": "Standup moved"}``
    """
    return {
        "uid": uid,
        "calendarId": calendar_id,
        "subject": str(event.get("subject") or ""),
        "location": str(event.get("location") or ""),
        "showAs": str(event.get("show_as") or "busy"),
        "sensitivity": str(event.get("sensitivity") or "normal"),
        "reminderMinutesBeforeStart": event.get("reminder_minutes"),
        "start": _iso(event.get("start")),
        "end": _iso(event.get("end")),
        "categories": list(event.get("categories") or []),
        "deleted": False,
        "modifiedAt": _now_iso(),
    }


def _create_receipt(local_key: str, calendar_id: str, event: dict[str, Any]) -> dict[str, Any]:
    """Build one POST receipt for an untagged local event.

    :param local_key: Entourage event id. Example: ``"3"``
    :param calendar_id: Target calendar. Example: ``"cal-work"``
    :param event: Entourage event. Example: ``{"subject": "Dentist"}``
    :return: Receipt dict. Example: ``{"created": True, "localKey": "3"}``
    """
    payload = _patch_receipt("", calendar_id, event)
    payload.pop("uid", None)
    payload["created"] = True
    payload["localKey"] = local_key
    return payload


def _write_receipt(new_dir: Path, payload: dict[str, Any], *, filename: str | None = None) -> None:
    """Write receipts/new/{uid|localKey}.json and log the beat.

    :param new_dir: receipts/new. Example: ``Path("receipts/new")``
    :param payload: Receipt. Example: ``{"uid": "evt-standup", "subject": "Moved"}``
    :param filename: Optional override. Example: ``"local-3.json"``
    :return: None
    """
    key = filename or f"{payload.get('uid') or payload.get('localKey')}.json"
    path = new_dir / key
    path.write_text(json.dumps(payload), encoding="utf-8")
    logger.info(
        "taskd.receipts | exit | uid=%s localKey=%s created=%s",
        payload.get("uid"),
        payload.get("localKey"),
        payload.get("created"),
    )


def _calendar_id_for_event(uid: str, uid_map: UidMap) -> str:
    """Best-effort calendar id when snapshot row is missing.

    :param uid: Graph event id. Example: ``"evt-standup"``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Calendar id or empty. Example: ``"cal-work"``
    """
    _ = uid
    if len(uid_map.calendars) == 1:
        return next(iter(uid_map.calendars))
    return ""


def _calendar_id_for_project(project_id: str, uid_map: UidMap) -> str:
    """Resolve Graph calendar id from Entourage project id.

    :param project_id: Entourage project id. Example: ``"10"``
    :param uid_map: Joins. Example: ``UidMap()``
    :return: Calendar id or empty. Example: ``"cal-work"``
    """
    for calendar_id, joined_project in uid_map.calendars.items():
        if joined_project == project_id:
            return calendar_id
    return ""


def _iso(value: Any) -> str | None:
    """Format datetime as ISO Z.

    :param value: Start/end field. Example: ``datetime(2026, 9, 15, 18, 0, tzinfo=timezone.utc)``
    :return: ISO string or None. Example: ``"2026-09-15T18:00:00Z"``
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        stamp = value.astimezone(timezone.utc)
        return stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(value)


def _now_iso() -> str:
    """UTC now as ISO Z.

    :return: Stamp. Example: ``"2026-09-11T16:10:00Z"``
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
