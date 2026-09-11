"""Publish Outlook calendar snapshot.json for Mac taskd (LibreELEC side)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from o365pop.graph.port import GraphPort

logger = logging.getLogger(__name__)

ATTACHMENT_MAX_BYTES = 5 * 1024 * 1024
RECEIPT_MAX_ATTEMPTS = 3


def publish(
    graph: GraphPort,
    dest: Path,
    *,
    past_days: int = 30,
    future_days: int = 180,
) -> dict[str, Any]:
    """Write calendars and events atomically to dest; attachment bytes beside snapshot.

    :param graph: GraphPort. Example: ``FileGraphAdapter(case_dir)``
    :param dest: snapshot.json path. Example: ``Path("var/calendar/snapshot.json")``
    :param past_days: calendarView past window. Example: ``30``
    :param future_days: calendarView future window. Example: ``180``
    :return: Counts. Example: ``{"calendars": 1, "events": 1, "bytes": 512}``
    """
    start_dt, end_dt = _window_bounds(past_days, future_days)
    start_iso = _iso_z(start_dt)
    end_iso = _iso_z(end_dt)
    calendars, events = _collect(graph, start_iso, end_iso)
    logger.info(
        "tosser.calendar_snapshot.publish | entry | calendars=%s events=%s",
        len(calendars),
        len(events),
    )
    attachments_root = dest.parent / "attachments"
    _write_attachment_files(graph, events, attachments_root)
    payload = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {"start": start_iso, "end": end_iso},
        "calendars": calendars,
        "events": events,
    }
    body = json.dumps(payload, indent=2)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.parent / f"{dest.name}.tmp"
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(dest)
    size = dest.stat().st_size
    logger.info("tosser.calendar_snapshot.publish | exit | path=%s bytes=%s", dest, size)
    return {"calendars": len(calendars), "events": len(events), "bytes": size}


def apply_receipts(graph: GraphPort, receipts_dir: Path, acks_dir: Path) -> dict[str, int]:
    """PATCH/POST/DELETE Graph from Mac calendar receipts.

    :param graph: GraphPort. Example: ``FileGraphAdapter(case_dir)``
    :param receipts_dir: ``calendar/receipts``. Example: ``Path("var/calendar/receipts")``
    :param acks_dir: ``calendar/acks`` for create acks. Example: ``Path("var/calendar/acks")``
    :return: Counts. Example: ``{"patched": 1, "created": 0, "deleted": 0}``
    """
    new_dir = receipts_dir / "new"
    sent_dir = receipts_dir / "sent"
    failed_dir = receipts_dir / "failed"
    sent_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)
    acks_dir.mkdir(parents=True, exist_ok=True)
    patched = created = deleted = 0
    if not new_dir.is_dir():
        return {"patched": 0, "created": 0, "deleted": 0}
    for path in sorted(new_dir.glob("*.json")):
        one = _apply_one_receipt(graph, path, sent_dir, failed_dir, acks_dir)
        patched += one["patched"]
        created += one["created"]
        deleted += one["deleted"]
    _apply_attachment_receipts(graph, new_dir / "attachments", sent_dir / "attachments", failed_dir / "attachments")
    return {"patched": patched, "created": created, "deleted": deleted}


def _apply_one_receipt(
    graph: GraphPort,
    path: Path,
    sent_dir: Path,
    failed_dir: Path,
    acks_dir: Path,
) -> dict[str, int]:
    """Apply one calendar receipt file.

    :param graph: GraphPort. Example: ``FileGraphAdapter(case_dir)``
    :param path: Receipt JSON. Example: ``Path("receipts/new/evt-standup.json")``
    :param sent_dir: Success dir. Example: ``Path("receipts/sent")``
    :param failed_dir: Failure dir. Example: ``Path("receipts/failed")``
    :param acks_dir: Create ack dir. Example: ``Path("calendar/acks")``
    :return: Counts. Example: ``{"patched": 1, "created": 0, "deleted": 0}``
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        counts = _dispatch_receipt(graph, payload, acks_dir)
        path.replace(sent_dir / path.name)
        return counts
    except Exception as exc:
        logger.error(
            "tosser.calendar_snapshot.apply_receipts | error | path=%s err=%s",
            path.name,
            type(exc).__name__,
        )
        _bump_or_fail(path, failed_dir)
        return {"patched": 0, "created": 0, "deleted": 0}


def _dispatch_receipt(graph: GraphPort, payload: dict[str, Any], acks_dir: Path) -> dict[str, int]:
    """PATCH, POST, or DELETE one Graph event from a receipt.

    :param graph: GraphPort. Example: ``FileGraphAdapter(case_dir)``
    :param payload: Receipt. Example: ``{"uid": "evt-standup", "subject": "Moved"}``
    :param acks_dir: Create ack dir. Example: ``Path("calendar/acks")``
    :return: Counts. Example: ``{"patched": 1, "created": 0, "deleted": 0}``
    """
    if payload.get("deleted") and payload.get("uid"):
        graph.delete_event(str(payload["uid"]))
        return {"patched": 0, "created": 0, "deleted": 1}
    if payload.get("created") and payload.get("localKey"):
        calendar_id = str(payload.get("calendarId") or payload.get("project") or "")
        created = graph.create_event(calendar_id, _create_body(payload))
        uid = str(created.get("id") or "")
        local_key = str(payload["localKey"])
        acks_dir.mkdir(parents=True, exist_ok=True)
        (acks_dir / f"{local_key}.json").write_text(json.dumps({"uid": uid}), encoding="utf-8")
        logger.info("tosser.calendar_snapshot.apply_receipts | exit | created=1 uid=%s localKey=%s", uid, local_key)
        return {"patched": 0, "created": 1, "deleted": 0}
    if payload.get("uid"):
        graph.patch_event(str(payload["uid"]), _patch_body(payload))
        return {"patched": 1, "created": 0, "deleted": 0}
    return {"patched": 0, "created": 0, "deleted": 0}


def _patch_body(payload: dict[str, Any]) -> dict[str, Any]:
    """Graph PATCH body from a calendar receipt (no attendees).

    :param payload: Receipt. Example: ``{"subject": "Standup moved", "location": "Room B"}``
    :return: Patch object. Example: ``{"subject": "Standup moved"}``
    """
    body: dict[str, Any] = {}
    for key in ("subject", "location", "showAs", "sensitivity"):
        if payload.get(key) is not None:
            body[key] = payload[key]
    if payload.get("reminderMinutesBeforeStart") is not None:
        body["reminderMinutesBeforeStart"] = int(payload["reminderMinutesBeforeStart"])
    if payload.get("start") and payload.get("end"):
        body["start"] = _graph_datetime(str(payload["start"]))
        body["end"] = _graph_datetime(str(payload["end"]))
    if payload.get("categories") is not None:
        body["categories"] = list(payload["categories"])
    return body


def _create_body(payload: dict[str, Any]) -> dict[str, Any]:
    """Graph POST body from a create receipt.

    :param payload: Receipt. Example: ``{"subject": "Dentist", "start": "...", "end": "..."}``
    :return: Event object. Example: ``{"subject": "Dentist", "start": {...}, "end": {...}}``
    """
    body = _patch_body(payload)
    body.setdefault("subject", str(payload.get("subject") or ""))
    if "start" not in body and payload.get("start"):
        body["start"] = _graph_datetime(str(payload["start"]))
    if "end" not in body and payload.get("end"):
        body["end"] = _graph_datetime(str(payload["end"]))
    return body


def _graph_datetime(value: str) -> dict[str, str]:
    """Wrap an ISO instant for Graph dateTimeTimeZone.

    :param value: ISO string. Example: ``"2026-09-15T18:00:00Z"``
    :return: Graph block. Example: ``{"dateTime": "2026-09-15T18:00:00", "timeZone": "UTC"}``
    """
    text = value.replace("Z", "")
    if "." in text:
        text = text.split(".", 1)[0]
    return {"dateTime": text, "timeZone": "UTC"}


def _apply_attachment_receipts(
    graph: GraphPort,
    new_dir: Path,
    sent_dir: Path,
    failed_dir: Path,
) -> None:
    """POST attachment bytes from receipt sidecar files.

    :param graph: GraphPort. Example: ``FileGraphAdapter(case_dir)``
    :param new_dir: ``receipts/new/attachments``. Example: ``Path("receipts/new/attachments")``
    :param sent_dir: Success dir. Example: ``Path("receipts/sent/attachments")``
    :param failed_dir: Failure dir. Example: ``Path("receipts/failed/attachments")``
    :return: None
    """
    if not new_dir.is_dir():
        return
    sent_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(new_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            event_id = str(payload["eventId"])
            name = str(payload["name"])
            content_type = str(payload.get("contentType") or "application/octet-stream")
            file_path = new_dir / str(payload.get("file") or name)
            content = file_path.read_bytes()
            graph.create_event_attachment(event_id, name, content_type, content)
            path.replace(sent_dir / path.name)
            if file_path.is_file():
                file_path.replace(sent_dir / file_path.name)
        except Exception as exc:
            logger.error(
                "tosser.calendar_snapshot.apply_receipts | error | attachment=%s err=%s",
                path.name,
                type(exc).__name__,
            )
            path.replace(failed_dir / path.name)


def _bump_or_fail(path: Path, failed_dir: Path) -> None:
    """Increment attempts or move to failed/.

    :param path: Receipt still in new/. Example: ``Path("receipts/new/evt-standup.json")``
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


def _collect(graph: GraphPort, start: str, end: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Pull editable calendars and calendarView events.

    :param graph: GraphPort. Example: ``FileGraphAdapter(case_dir)``
    :param start: Window start ISO. Example: ``"2026-08-12T00:00:00Z"``
    :param end: Window end ISO. Example: ``"2027-03-10T00:00:00Z"``
    :return: calendars, events. Example: ``([{...}], [{...}])``
    """
    calendars = [_public_calendar(row) for row in graph.list_calendars()]
    events: list[dict[str, Any]] = []
    for row in calendars:
        calendar_id = str(row["id"])
        for event in graph.list_calendar_view(calendar_id, start, end):
            events.append(_public_event(event, calendar_id, graph))
    return calendars, events


def _public_calendar(row: dict[str, Any]) -> dict[str, Any]:
    """Keep snapshot calendar fields.

    :param row: Graph calendar. Example: ``{"id": "cal-work", "displayName": "Work"}``
    :return: Snapshot calendar. Example: ``{"id": "cal-work", "displayName": "Work"}``
    """
    return {
        "id": str(row.get("id") or ""),
        "displayName": str(row.get("displayName") or ""),
        "isDefault": bool(row.get("isDefault")),
    }


def _public_event(row: dict[str, Any], calendar_id: str, graph: GraphPort) -> dict[str, Any]:
    """Flatten one calendarView row onto the snapshot contract.

    :param row: Graph event. Example: ``{"id": "evt-standup", "subject": "Standup"}``
    :param calendar_id: Parent calendar. Example: ``"cal-work"``
    :param graph: GraphPort for attachment metadata. Example: ``FileGraphAdapter(case_dir)``
    :return: Snapshot event. Example: ``{"id": "evt-standup", "calendarId": "cal-work"}``
    """
    categories = row.get("categories") or []
    names = [str(item) for item in categories] if isinstance(categories, list) else []
    event_id = str(row.get("id") or "")
    attachments = [_public_attachment(att) for att in graph.list_event_attachments(event_id)]
    return {
        "id": event_id,
        "calendarId": calendar_id,
        "subject": str(row.get("subject") or ""),
        "start": _public_datetime(row.get("start")),
        "end": _public_datetime(row.get("end")),
        "isAllDay": bool(row.get("isAllDay")),
        "location": _location_text(row.get("location")),
        "bodyPreview": str(row.get("bodyPreview") or ""),
        "categories": names,
        "attendees": _public_attendees(row.get("attendees") or []),
        "isOrganizer": bool(row.get("isOrganizer")),
        "type": str(row.get("type") or "singleInstance"),
        "showAs": str(row.get("showAs") or "busy"),
        "sensitivity": str(row.get("sensitivity") or "normal"),
        "reminderMinutesBeforeStart": row.get("reminderMinutesBeforeStart"),
        "lastModifiedDateTime": str(row.get("lastModifiedDateTime") or ""),
        "attachments": attachments,
    }


def _public_attachment(row: dict[str, Any]) -> dict[str, str]:
    """Keep attachment metadata only.

    :param row: Graph attachment. Example: ``{"name": "agenda.pdf", "contentType": "application/pdf"}``
    :return: Snapshot attachment. Example: ``{"name": "agenda.pdf", "contentType": "application/pdf"}``
    """
    return {
        "name": str(row.get("name") or ""),
        "contentType": str(row.get("contentType") or "application/octet-stream"),
    }


def _public_attendees(rows: list[Any]) -> list[dict[str, str]]:
    """Flatten Graph attendees to display names (no invite PATCH).

    :param rows: Graph attendees. Example: ``[{"emailAddress": {"name": "Ada", "address": "ada@contoso.com"}}]``
    :return: Snapshot attendees. Example: ``[{"name": "Ada", "email": "ada@contoso.com", "type": "required"}]``
    """
    attendees: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if "email" in row:
            attendees.append(
                {
                    "name": str(row.get("name") or ""),
                    "email": str(row.get("email") or ""),
                    "type": str(row.get("type") or "required"),
                }
            )
            continue
        email = row.get("emailAddress") if isinstance(row.get("emailAddress"), dict) else {}
        attendees.append(
            {
                "name": str(email.get("name") or ""),
                "email": str(email.get("address") or ""),
                "type": str(row.get("type") or "required"),
            }
        )
    return attendees


def _public_datetime(value: Any) -> dict[str, str]:
    """Normalize Graph dateTime block to snapshot shape.

    :param value: Graph start/end. Example: ``{"dateTime": "2026-09-12T13:00:00.0000000", "timeZone": "UTC"}``
    :return: Snapshot block. Example: ``{"dateTime": "2026-09-12T13:00:00Z", "timeZone": "UTC"}``
    """
    if isinstance(value, dict):
        raw = str(value.get("dateTime") or "").strip()
        zone = str(value.get("timeZone") or "UTC")
        return {"dateTime": _iso_z_from_graph(raw), "timeZone": zone}
    text = str(value or "").strip()
    return {"dateTime": _iso_z_from_graph(text), "timeZone": "UTC"}


def _location_text(value: Any) -> str:
    """Extract location displayName or plain string.

    :param value: Graph location. Example: ``{"displayName": "Room A"}``
    :return: Location string. Example: ``"Room A"``
    """
    if isinstance(value, dict):
        return str(value.get("displayName") or "")
    return str(value or "")


def _write_attachment_files(graph: GraphPort, events: list[dict[str, Any]], root: Path) -> None:
    """Copy attachment bytes beside the snapshot (skip oversize files).

    :param graph: GraphPort. Example: ``FileGraphAdapter(case_dir)``
    :param events: Published events with attachment metadata. Example: ``[{"id": "evt-standup"}]``
    :param root: ``calendar/attachments``. Example: ``Path("var/calendar/attachments")``
    :return: None
    """
    for event in events:
        event_id = str(event.get("id") or "")
        if not event_id:
            continue
        attachments = graph.list_event_attachments(event_id)
        for att in attachments:
            att_id = str(att.get("id") or "")
            name = str(att.get("name") or att_id or "attachment")
            if not att_id:
                continue
            try:
                content = graph.get_event_attachment_bytes(event_id, att_id)
            except OSError:
                logger.warning(
                    "tosser.calendar_snapshot.publish | branch | attachment_skipped=true reason=read_failed event=%s",
                    event_id,
                )
                continue
            if len(content) > ATTACHMENT_MAX_BYTES:
                logger.warning(
                    "tosser.calendar_snapshot.publish | branch | attachment_skipped=true event=%s name=%s bytes=%s",
                    event_id,
                    name,
                    len(content),
                )
                continue
            dest = root / event_id / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)


def _window_bounds(past_days: int, future_days: int) -> tuple[datetime, datetime]:
    """UTC calendarView window.

    :param past_days: Days before now. Example: ``30``
    :param future_days: Days after now. Example: ``180``
    :return: (start, end). Example: ``(datetime(...), datetime(...))``
    """
    now = datetime.now(UTC)
    start = now - timedelta(days=past_days)
    end = now + timedelta(days=future_days)
    return start, end


def _iso_z(value: datetime) -> str:
    """Format aware datetime as ISO Z.

    :param value: UTC datetime. Example: ``datetime(2026, 8, 12, tzinfo=UTC)``
    :return: ISO string. Example: ``"2026-08-12T00:00:00Z"``
    """
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_z_from_graph(raw: str) -> str:
    """Normalize Graph dateTime to ISO Z.

    :param raw: Graph dateTime. Example: ``"2026-09-12T13:00:00.0000000"``
    :return: ISO Z. Example: ``"2026-09-12T13:00:00Z"``
    """
    text = raw.strip()
    if not text:
        return ""
    if text.endswith("Z"):
        return text
    if "." in text:
        text = text.split(".", 1)[0]
    return f"{text}Z"
