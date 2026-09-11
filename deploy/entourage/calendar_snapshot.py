"""Parse LibreELEC ``calendar/snapshot.json`` (stdlib only)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class CalendarSnapshotError(ValueError):
    """Raised when a calendar snapshot object is missing a required id."""


@dataclass(frozen=True)
class SnapshotWindow:
    """calendarView window echoed in the snapshot.

    :param start: Window start ISO. Example: ``"2026-08-12T00:00:00Z"``
    :param end: Window end ISO. Example: ``"2027-03-10T00:00:00Z"``
    """

    start: str
    end: str


@dataclass(frozen=True)
class SnapshotCalendar:
    """One Outlook calendar row.

    :param id: Graph calendar id. Example: ``"cal-work"``
    :param display_name: Calendar title. Example: ``"Work"``
    :param is_default: Default mailbox calendar flag. Example: ``False``
    """

    id: str
    display_name: str
    is_default: bool


@dataclass(frozen=True)
class SnapshotDateTime:
    """Graph start/end block.

    :param date_time: ISO instant. Example: ``"2026-09-12T13:00:00Z"``
    :param time_zone: IANA or UTC label. Example: ``"UTC"``
    """

    date_time: str
    time_zone: str


@dataclass(frozen=True)
class SnapshotAttendee:
    """Meeting attendee for display in content (not invites).

    :param name: Display name. Example: ``"Ada Lovelace"``
    :param email: SMTP address. Example: ``"ada@contoso.com"``
    :param type: Graph attendee type. Example: ``"required"``
    """

    name: str
    email: str
    type: str


@dataclass(frozen=True)
class SnapshotAttachment:
    """Attachment metadata (bytes live beside the snapshot).

    :param name: File name. Example: ``"agenda.pdf"``
    :param content_type: MIME type. Example: ``"application/pdf"``
    """

    name: str
    content_type: str


@dataclass(frozen=True)
class SnapshotEvent:
    """One calendarView occurrence row.

    :param id: Graph event or occurrence id. Example: ``"evt-standup"``
    :param calendar_id: Parent calendar id. Example: ``"cal-work"``
    :param subject: Event title. Example: ``"Standup"``
    :param start: Start instant. Example: ``SnapshotDateTime("2026-09-12T13:00:00Z", "UTC")``
    :param end: End instant. Example: ``SnapshotDateTime("2026-09-12T13:30:00Z", "UTC")``
    :param is_all_day: All-day flag. Example: ``False``
    :param location: Location string. Example: ``"Room A"``
    :param body_preview: Plain body preview. Example: ``"Daily"``
    :param categories: Category names. Example: ``("Work",)``
    :param attendees: Attendee rows. Example: ``()``
    :param show_as: Graph showAs. Example: ``"busy"``
    :param sensitivity: Graph sensitivity. Example: ``"normal"``
    :param reminder_minutes: Reminder offset. Example: ``15``
    :param last_modified: Graph stamp or None. Example: ``"2026-09-11T15:00:00Z"``
    :param attachments: Attachment metadata. Example: ``()``
    """

    id: str
    calendar_id: str
    subject: str
    start: SnapshotDateTime
    end: SnapshotDateTime
    is_all_day: bool
    location: str
    body_preview: str
    categories: tuple[str, ...]
    attendees: tuple[SnapshotAttendee, ...]
    show_as: str
    sensitivity: str
    reminder_minutes: int | None
    last_modified: str | None
    attachments: tuple[SnapshotAttachment, ...]


@dataclass(frozen=True)
class CalendarSnapshot:
    """Validated calendar snapshot document.

    :param generated_at: Publisher stamp. Example: ``"2026-09-11T16:00:00Z"``
    :param window: Sync window. Example: ``SnapshotWindow("", "")``
    :param calendars: Mailbox calendars. Example: ``()``
    :param events: Occurrences in window. Example: ``()``
    """

    generated_at: str
    window: SnapshotWindow
    calendars: tuple[SnapshotCalendar, ...]
    events: tuple[SnapshotEvent, ...]


def parse_calendar_snapshot(payload: dict[str, Any]) -> CalendarSnapshot:
    """Validate a calendar snapshot dict and return typed rows.

    :param payload: Decoded JSON object. Example: ``{"calendars": [{"id": "cal-work"}]}``
    :return: CalendarSnapshot. Example: ``CalendarSnapshot(generated_at="", ...)``
    :raises CalendarSnapshotError: if a calendar or event is missing ``id``
    :raises TypeError: if payload is not a dict
    """
    logger.info(
        "taskd.calendar_snapshot.parse | entry | keys=%s",
        sorted(payload.keys()) if isinstance(payload, dict) else type(payload),
    )
    if not isinstance(payload, dict):
        raise TypeError("calendar snapshot payload must be a dict")
    window_raw = payload.get("window") if isinstance(payload.get("window"), dict) else {}
    snapshot = CalendarSnapshot(
        generated_at=str(payload.get("generated_at") or ""),
        window=SnapshotWindow(
            start=str(window_raw.get("start") or ""),
            end=str(window_raw.get("end") or ""),
        ),
        calendars=tuple(_parse_calendar(row) for row in _as_rows(payload.get("calendars"))),
        events=tuple(_parse_event(row) for row in _as_rows(payload.get("events"))),
    )
    logger.info(
        "taskd.calendar_snapshot.parse | exit | calendars=%s events=%s",
        len(snapshot.calendars),
        len(snapshot.events),
    )
    return snapshot


def _as_rows(value: Any) -> list[dict[str, Any]]:
    """Coerce a JSON array of objects.

    :param value: Raw calendars/events value. Example: ``[{"id": "cal-work"}]``
    :return: Object rows. Example: ``[{"id": "cal-work"}]``
    :raises CalendarSnapshotError: if an item is not an object
    """
    if value is None:
        return []
    if not isinstance(value, list):
        raise CalendarSnapshotError("snapshot collection must be a list")
    rows: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise CalendarSnapshotError("snapshot row must be an object")
        rows.append(item)
    return rows


def _require_id(row: dict[str, Any], kind: str) -> str:
    """Return a non-empty id or raise.

    :param row: Snapshot object. Example: ``{"id": "evt-standup"}``
    :param kind: Row kind for the error. Example: ``"event"``
    :return: Id string. Example: ``"evt-standup"``
    :raises CalendarSnapshotError: if ``id`` is missing or blank
    """
    raw = row.get("id")
    if raw is None or str(raw).strip() == "":
        raise CalendarSnapshotError(f"{kind} missing id")
    return str(raw)


def _parse_calendar(row: dict[str, Any]) -> SnapshotCalendar:
    """Build one calendar row.

    :param row: Raw calendar. Example: ``{"id": "cal-work", "displayName": "Work"}``
    :return: SnapshotCalendar. Example: ``SnapshotCalendar(id="cal-work", display_name="Work", is_default=False)``
    :raises CalendarSnapshotError: if id is missing
    """
    return SnapshotCalendar(
        id=_require_id(row, "calendar"),
        display_name=str(row.get("displayName") or row.get("display_name") or ""),
        is_default=bool(row.get("isDefault") or row.get("is_default")),
    )


def _parse_event(row: dict[str, Any]) -> SnapshotEvent:
    """Build one event row.

    :param row: Raw event. Example: ``{"id": "evt-standup", "calendarId": "cal-work", "subject": "Standup"}``
    :return: SnapshotEvent. Example: ``SnapshotEvent(id="evt-standup", ...)``
    :raises CalendarSnapshotError: if id is missing
    """
    categories = row.get("categories") or []
    names = tuple(str(item) for item in categories) if isinstance(categories, list) else ()
    attendees = tuple(_parse_attendee(item) for item in _as_rows(row.get("attendees")))
    attachments = tuple(_parse_attachment(item) for item in _as_rows(row.get("attachments")))
    reminder = row.get("reminderMinutesBeforeStart")
    if reminder is None:
        reminder = row.get("reminder_minutes")
    return SnapshotEvent(
        id=_require_id(row, "event"),
        calendar_id=str(row.get("calendarId") or row.get("calendar_id") or ""),
        subject=str(row.get("subject") or ""),
        start=_parse_datetime(row.get("start")),
        end=_parse_datetime(row.get("end")),
        is_all_day=bool(row.get("isAllDay") or row.get("is_all_day")),
        location=str(row.get("location") or ""),
        body_preview=str(row.get("bodyPreview") or row.get("body_preview") or ""),
        categories=names,
        attendees=attendees,
        show_as=str(row.get("showAs") or row.get("show_as") or "busy"),
        sensitivity=str(row.get("sensitivity") or "normal"),
        reminder_minutes=int(reminder) if reminder is not None else None,
        last_modified=_optional_str(row.get("lastModifiedDateTime") or row.get("last_modified")),
        attachments=attachments,
    )


def _parse_datetime(value: Any) -> SnapshotDateTime:
    """Normalize Graph dateTime block or ISO string.

    :param value: Raw start/end. Example: ``{"dateTime": "2026-09-12T13:00:00Z", "timeZone": "UTC"}``
    :return: SnapshotDateTime. Example: ``SnapshotDateTime("2026-09-12T13:00:00Z", "UTC")``
    """
    if isinstance(value, dict):
        raw = str(value.get("dateTime") or value.get("date_time") or "").strip()
        zone = str(value.get("timeZone") or value.get("time_zone") or "UTC")
        if raw and not raw.endswith("Z") and "." not in raw:
            raw = f"{raw}Z"
        return SnapshotDateTime(date_time=raw, time_zone=zone)
    text = str(value or "").strip()
    return SnapshotDateTime(date_time=text, time_zone="UTC")


def _parse_attendee(row: dict[str, Any]) -> SnapshotAttendee:
    """Build one attendee row.

    :param row: Raw attendee. Example: ``{"name": "Ada", "email": "ada@contoso.com", "type": "required"}``
    :return: SnapshotAttendee. Example: ``SnapshotAttendee(name="Ada", email="ada@contoso.com", type="required")``
    """
    return SnapshotAttendee(
        name=str(row.get("name") or ""),
        email=str(row.get("email") or row.get("address") or ""),
        type=str(row.get("type") or "required"),
    )


def _parse_attachment(row: dict[str, Any]) -> SnapshotAttachment:
    """Build one attachment metadata row.

    :param row: Raw attachment. Example: ``{"name": "agenda.pdf", "contentType": "application/pdf"}``
    :return: SnapshotAttachment. Example: ``SnapshotAttachment(name="agenda.pdf", content_type="application/pdf")``
    """
    return SnapshotAttachment(
        name=str(row.get("name") or ""),
        content_type=str(row.get("contentType") or row.get("content_type") or "application/octet-stream"),
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
