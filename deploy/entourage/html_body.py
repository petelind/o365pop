"""Graph HTML bodies for Entourage calendar events (stdlib only)."""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser

_HTML_MARKERS = ("<p>", "<p ", "<div", "<br", "<html", "<span", "<table", "<a ")
_BLOCK_TAGS = frozenset({"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4"})


def is_html_body(body: str, content_type: str) -> bool:
    """True when Graph declares html or the payload looks like markup.

    :param body: Graph body content. Example: ``"<p>Ship it</p>"``
    :param content_type: Graph contentType. Example: ``"html"``
    :return: Whether Entourage should use HTML content. Example: ``True``
    """
    if content_type.lower() == "html":
        return True
    head = body.lstrip()[:200].lower()
    return any(marker in head for marker in _HTML_MARKERS)


def as_html_document(fragment: str) -> str:
    """Wrap a Graph HTML fragment for Entourage 2008.

    :param fragment: Graph HTML. Example: ``"<p>Ship it</p>"``
    :return: Full HTML document. Example: ``"<html><body><p>Ship it</p></body></html>"``
    """
    if "<html" in fragment.lower():
        return fragment
    return f"<html><body>{fragment}</body></html>"


def html_to_plain(markup: str) -> str:
    """Strip tags and unescape entities for plain-text Entourage content.

    :param markup: Graph HTML. Example: ``"<p>Thank you&nbsp;!</p>"``
    :return: Readable plain text. Example: ``"Thank you !"``
    """
    parser = _PlainExtractor()
    parser.feed(markup)
    parser.close()
    text = unescape("".join(parser.parts)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def merge_html(*fragments: str) -> str:
    """Join HTML fragments into one document body.

    :param fragments: HTML snippets. Example: ``("<p>uid</p>", "<p>Hi</p>")``
    :return: Combined HTML document. Example: ``"<html><body>...</body></html>"``
    """
    parts = [fragment.strip() for fragment in fragments if fragment and fragment.strip()]
    inner = "".join(parts)
    return as_html_document(inner)


class _PlainExtractor(HTMLParser):
    """Collect visible text; treat block tags as line breaks."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCK_TAGS and tag != "br":
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)
