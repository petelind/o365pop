"""LibreELEC snapshot bodies are plain text: Graph Prefer, else BeautifulSoup."""

from __future__ import annotations

import logging

import pytest

from o365pop.tosser.plain_body import snapshot_plain_body


@pytest.mark.unit
def test_snapshot_plain_body_keeps_graph_text() -> None:
    """Prefer-honored text is published as-is.

    :return: None
    """
    text, content_type, source = snapshot_plain_body("Log all expenses (5min)", "text")
    assert text == "Log all expenses (5min)"
    assert content_type == "text"
    assert source == "graph"


@pytest.mark.unit
def test_snapshot_plain_body_soups_html_when_prefer_ignored() -> None:
    """HTML leftover after calendarView is stripped on LibreELEC.

    :return: None
    """
    soup = (
        "<html><head><style>.EmailQuote { color: red; }</style></head>"
        '<body><div class="PlainText">Log all expenses (5min)</div></body></html>'
    )
    text, content_type, source = snapshot_plain_body(soup, "html")
    assert source == "beautifulsoup"
    assert content_type == "text"
    assert "Log all expenses (5min)" in text
    assert "<" not in text
    assert "EmailQuote" not in text


@pytest.mark.unit
def test_snapshot_plain_body_soups_html_labeled_as_text() -> None:
    """Prefer may set contentType=text while leaving markup; still soup.

    :return: None
    """
    text, content_type, source = snapshot_plain_body("<p>Log all expenses (5min)</p>", "text")
    assert source == "beautifulsoup"
    assert content_type == "text"
    assert text == "Log all expenses (5min)"


@pytest.mark.unit
@pytest.mark.log_story
def test_public_event_logs_soup_fallback(caplog: pytest.LogCaptureFixture) -> None:
    """Publish logs which body path ran.

    :param caplog: pytest log capture
    :return: None
    """
    from o365pop.tosser.calendar_snapshot import _public_event

    caplog.set_level(logging.INFO)
    event = _public_event(
        {
            "id": "evt-standup",
            "subject": "Standup",
            "body": {"contentType": "html", "content": "<p>Please review the <strong>deck</strong>.</p>"},
        },
        "cal-work",
        graph=None,
    )
    assert event["bodyContentType"] == "text"
    assert "deck" in event["body"]
    assert "<strong>" not in event["body"]
    assert any("body_plain=beautifulsoup" in rec.getMessage() for rec in caplog.records)
