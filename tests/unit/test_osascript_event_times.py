"""CAL deploy bug — Entourage events must get Graph start/end, not creation time."""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from deploy.entourage.osascript_entourage import (
    _applescript_date,
    _event_assigns,
    _event_content_prop,
    _event_create_script,
)


@pytest.mark.unit
def test_event_create_script_sets_start_and_end_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """Create script must pass start time and end time to Entourage.

    :param monkeypatch: TZ override for deterministic local formatting
    :return: None
    """
    monkeypatch.setenv("TZ", "America/New_York")
    time.tzset()
    start = datetime(2026, 9, 12, 13, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 12, 13, 30, tzinfo=timezone.utc)
    script = _event_create_script(
        {
            "subject": "Standup",
            "content_plain": "o365pop-uid: evt-standup",
            "start": start,
            "end": end,
        }
    )
    start_literal = _applescript_date(start)
    end_literal = _applescript_date(end)
    assert f'start time:date "{start_literal}"' in script
    assert f'end time:date "{end_literal}"' in script
    assert "09:00:00 AM" in script
    assert "09:30:00 AM" in script


@pytest.mark.unit
def test_event_assigns_sets_start_and_end_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """Update script must patch start time and end time.

    :param monkeypatch: TZ override
    :return: None
    """
    monkeypatch.setenv("TZ", "America/New_York")
    time.tzset()
    start = datetime(2026, 9, 15, 18, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 15, 19, 0, tzinfo=timezone.utc)
    body = _event_assigns({"start": start, "end": end})
    assert f'set start time of e to date "{_applescript_date(start)}"' in body
    assert f'set end time of e to date "{_applescript_date(end)}"' in body


@pytest.mark.unit
def test_event_create_script_sets_project_list_and_categories() -> None:
    """Create script must bind Project and category list (CAL1.1 / CAL1.5).

    :return: None
    """
    script = _event_create_script(
        {
            "subject": "Standup",
            "project_id": "12",
            "categories": ["Work", "Urgent"],
        }
    )
    assert "project list:{project id 12}" in script
    assert "set project list of e to {project id 12}" in script
    assert 'set category of e to {category "Work", category "Urgent"}' in script


@pytest.mark.unit
def test_event_assigns_sets_project_list_and_categories() -> None:
    """Update script must patch Project and categories.

    :return: None
    """
    body = _event_assigns({"project_id": "7", "categories": ["PARTOFSHIP"]})
    assert "set project list of e to {project id 7}" in body
    assert 'set category of e to {category "PARTOFSHIP"}' in body


@pytest.mark.unit
def test_event_create_script_uses_content_for_html_body() -> None:
    """Create script must set ``content`` after create, not inside ``with properties``.

    :return: None
    """
    script = _event_create_script(
        {
            "subject": "Standup",
            "content_html": "<html><body><p>Ship it</p></body></html>",
        }
    )
    assert "make new event with properties {subject:" in script
    assert "plain text content:" not in script.split("make new event")[1].split("\n")[0]
    assert 'set content of e to "<html><body><p>Ship it</p></body></html>"' in script
    assert 'log "event_create make"' in script
    assert 'log "event_create content"' in script


@pytest.mark.unit
def test_event_create_script_empty_html_notes_use_content_not_plain_text_content() -> None:
    """Entourage events have no ``plain text content``; empty Graph HTML must use ``content``.

    Live -1728 ``Can't get content`` on LinkedIn/Gamma/New feature recurrences
    (bodyContentType=html, body empty) used ``set plain text content``.

    :return: None
    """
    script = _event_create_script(
        {
            "subject": "LinkedIn: read -> either comment or post",
            "content_plain": "o365pop-uid: evt-linkedin",
        }
    )
    assert "plain text content" not in script
    assert 'set content of e to "o365pop-uid: evt-linkedin"' in script


@pytest.mark.unit
def test_event_create_script_uses_content_for_text_body() -> None:
    """Plain Graph bodies must use ``content`` after create (events have no plain-text property).

    :return: None
    """
    prop = _event_content_prop({"content_plain": "Daily standup notes"})
    assert prop == 'content:"Daily standup notes"'
    script = _event_create_script({"subject": "Standup", "content_plain": "Daily standup notes"})
    props_line = next(line for line in script.splitlines() if "make new event" in line)
    assert "plain text content" not in script
    assert "plain text content:" not in props_line
    assert 'set content of e to "Daily standup notes"' in script


@pytest.mark.unit
def test_event_create_script_html_falls_back_to_plain_content() -> None:
    """Exchange HTML that Entourage rejects must fall back to ``content`` plain text.

    :return: None
    """
    script = _event_create_script(
        {
            "subject": "Taming the AI: Knowledge Sharing sessions(part 2)",
            "content_html": '<html><head><meta content="text/html"></head><body><p>Hi</p></body></html>',
            "content_plain": "o365pop-uid: evt-zoom",
        }
    )
    assert "plain text content" not in script
    assert "on error" in script
    assert 'set content of e to "o365pop-uid: evt-zoom"' in script
    assert "meta content=" in script


@pytest.mark.unit
def test_event_create_script_zoom_meeting_with_colon_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: colon subject + Zoom location + plain body must not hit AppleScript -2741.

    :param monkeypatch: TZ override
    :return: None
    """
    monkeypatch.setenv("TZ", "America/New_York")
    time.tzset()
    start = datetime(2026, 9, 11, 17, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 11, 18, 0, tzinfo=timezone.utc)
    script = _event_create_script(
        {
            "subject": "Taming the AI: Knowledge Sharing sessions(part 2)",
            "location": "https://vropco-ai.zoom.us/j/92399182989?pwd=QoNy0iWZ1on0PFcZjNoJKa0vBlHYRl.1",
            "content_plain": "o365pop-uid: evt-zoom",
            "project_id": "40",
            "categories": ["PARTOFSHIP"],
            "start": start,
            "end": end,
        }
    )
    props_line = next(line for line in script.splitlines() if "make new event" in line)
    assert "plain text content" not in script
    assert "Taming the AI: Knowledge Sharing sessions(part 2)" in props_line
    assert 'set content of e to "o365pop-uid: evt-zoom"' in script
    assert 'set category of e to {category "PARTOFSHIP"}' in script
