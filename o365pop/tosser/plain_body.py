"""Publish already-plain calendar notes on LibreELEC (Graph Prefer, else BeautifulSoup)."""

from __future__ import annotations

import logging
import re
from html import unescape

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_SKIP_TAGS = ("script", "style", "head", "meta", "link")
_HTML_MARKERS = ("<html", "<body", "<div", "<p>", "<p ", "<br", "<span", "<table")


def snapshot_plain_body(content: str, content_type: str) -> tuple[str, str, str]:
    """Return snapshot notes as text, using Graph text or BeautifulSoup.

    :param content: Graph body.content. Example: ``"<p>deck</p>"``
    :param content_type: Graph body.contentType. Example: ``"html"``
    :return: text, contentType, source. Example: ``("deck", "text", "beautifulsoup")``
    """
    incoming = (content_type or "text").strip().lower()
    if not content.strip():
        logger.info("tosser.plain_body.snapshot_plain_body | body_plain=empty | content_type_in=%s", incoming)
        return "", "text", "empty"
    if incoming != "html" and not _looks_like_html(content):
        logger.info("tosser.plain_body.snapshot_plain_body | body_plain=graph | content_type_in=%s", incoming)
        return content, "text", "graph"
    plain = _soup_plain(content)
    logger.info("tosser.plain_body.snapshot_plain_body | body_plain=beautifulsoup | content_type_in=%s", incoming)
    return plain, "text", "beautifulsoup"


def _looks_like_html(content: str) -> bool:
    """True when Prefer was ignored and the body still looks like markup.

    :param content: Body text. Example: ``"<html><body>Hi</body></html>"``
    :return: Whether to run BeautifulSoup. Example: ``True``
    """
    stripped = content.lstrip().lower()
    if stripped.startswith("<"):
        return True
    return any(marker in stripped for marker in _HTML_MARKERS)


def _soup_plain(markup: str) -> str:
    """Strip tags, skip style/script, keep visible notes.

    :param markup: HTML leftover. Example: ``"<style>.x{}</style><div>Hi</div>"``
    :return: Plain notes. Example: ``"Hi"``
    """
    soup = BeautifulSoup(markup, "html.parser")
    for tag in soup(_SKIP_TAGS):
        tag.decompose()
    text = unescape(soup.get_text("\n")).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", text).strip()
