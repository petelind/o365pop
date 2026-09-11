"""CAL BPE-09 — Graph HTML bodies for Entourage calendar events."""

from __future__ import annotations

import pytest

from deploy.entourage.html_body import as_html_document, html_to_plain, is_html_body, merge_html


@pytest.mark.unit
def test_is_html_body_when_graph_declares_html() -> None:
    """Graph contentType html must use Entourage HTML content.

    :return: None
    """
    assert is_html_body("plain words", "html") is True


@pytest.mark.unit
def test_is_html_body_when_markup_without_content_type() -> None:
    """Untyped markup must still route to HTML content.

    :return: None
    """
    assert is_html_body("<p>Ship it</p>", "text") is True


@pytest.mark.unit
def test_html_to_plain_strips_tags_and_entities() -> None:
    """Mislabeled HTML must not become tag soup in plain text content.

    :return: None
    """
    assert html_to_plain("<p>Thank you&nbsp;!</p>") == "Thank you !"


@pytest.mark.unit
def test_merge_html_wraps_uid_and_graph_body() -> None:
    """Uid metadata and Graph HTML merge into one Entourage document.

    :return: None
    """
    doc = merge_html("<p>o365pop-uid: evt-standup</p>", "<p>Please review the <strong>deck</strong>.</p>")
    assert doc.startswith("<html><body>")
    assert "o365pop-uid: evt-standup" in doc
    assert "<strong>deck</strong>" in doc
    assert as_html_document("<p>Hi</p>") == "<html><body><p>Hi</p></body></html>"
