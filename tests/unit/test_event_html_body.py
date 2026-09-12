"""CAL — Entourage event notes are plain text; Graph HTML must be stripped."""

from __future__ import annotations

import pytest

from deploy.entourage.apply import parse_uid
from deploy.entourage.calendar_apply import _event_body_fields
from deploy.entourage.calendar_snapshot import SnapshotAttendee, SnapshotDateTime, SnapshotEvent


def _standup_row(*, body: str = "", body_type: str = "text") -> SnapshotEvent:
    return SnapshotEvent(
        id="evt-standup",
        calendar_id="cal-work",
        subject="Standup",
        start=SnapshotDateTime(date_time="2026-09-12T13:00:00Z", time_zone="UTC"),
        end=SnapshotDateTime(date_time="2026-09-12T13:30:00Z", time_zone="UTC"),
        is_all_day=False,
        location="Room A",
        body_preview="Daily",
        body=body,
        body_content_type=body_type,
        categories=("Work",),
        attendees=(SnapshotAttendee(name="Ada Lovelace", email="ada@contoso.com", type="required"),),
        show_as="busy",
        sensitivity="normal",
        reminder_minutes=15,
        last_modified="2026-09-11T15:00:00Z",
        attachments=(),
    )


@pytest.mark.unit
def test_event_body_fields_strips_graph_html_to_plain() -> None:
    """Event notes have no HTML property; tags must not appear in content.

    :return: None
    """
    fields = _event_body_fields(_standup_row(body="<p>Please review the <strong>deck</strong>.</p>", body_type="html"))
    assert "content_html" not in fields
    assert fields["content_plain"]
    assert "o365pop-uid: evt-standup" in fields["content_plain"]
    assert "deck" in fields["content_plain"]
    assert "<p>" not in fields["content_plain"]
    assert "<strong>" not in fields["content_plain"]
    assert "strong" not in fields["content_plain"]


@pytest.mark.unit
def test_event_body_fields_strips_exchange_plaintext_wrapper() -> None:
    """Outlook 'converted from text' HTML must become readable notes.

    :return: None
    """
    soup = (
        '<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8">'
        '<meta name="Generator" content="Microsoft Exchange Server">'
        '</head><body><div class="PlainText">Log all expenses (5min)</div></body></html>'
    )
    fields = _event_body_fields(_standup_row(body=soup, body_type="html"))
    assert "content_html" not in fields
    assert "Log all expenses (5min)" in fields["content_plain"]
    assert "<html>" not in fields["content_plain"]
    assert "<div" not in fields["content_plain"]
    assert "Generator" not in fields["content_plain"]


@pytest.mark.unit
def test_parse_uid_finds_graph_id_inside_html_content() -> None:
    """Receipt queue must still resolve uid if a live event still has leftover HTML.

    :return: None
    """
    html = "<html><body><p>o365pop-uid: evt-standup</p><p>Hi</p></body></html>"
    assert parse_uid(html) == "evt-standup"
