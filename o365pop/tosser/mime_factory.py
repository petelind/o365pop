"""Synthesize Teams RFC822 with reply-map headers (never a real SMTP From)."""

from __future__ import annotations

import logging
import re
from email.message import EmailMessage
from html import unescape
from html.parser import HTMLParser

from o365pop.tosser.chat_address import LOCAL_DOMAIN, encode_chat_id, reply_address

logger = logging.getLogger(__name__)

_HTML_MARKERS = ("<p>", "<p ", "<div", "<br", "<html", "<span", "<at ")
_BLOCK_TAGS = frozenset({"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4"})


def teams_to_rfc822(
    *,
    chat_id: str,
    graph_message_id: str,
    from_name: str,
    body: str,
    chat_subject: str,
    body_content_type: str = "text",
) -> EmailMessage:
    """Build a tossed Teams message.

    :param chat_id: Graph chat id. Example: ``"19:general"``
    :param graph_message_id: Graph message id. Example: ``"abc"``
    :param from_name: Display name. Example: ``"Ada Lovelace"``
    :param body: Chat text or HTML. Example: ``"<p>Ship it</p>"``
    :param chat_subject: Chat title. Example: ``"general"``
    :param body_content_type: Graph body type. Example: ``"html"``
    :return: EmailMessage with teams.* From/Reply-To and minted Message-ID.
    """
    logger.info(
        "tosser.mime_factory.teams_to_rfc822 | entry | chat_id=%s from_name=%s body_type=%s",
        chat_id,
        from_name,
        body_content_type,
    )
    address = reply_address(chat_id)
    chat_b32 = encode_chat_id(chat_id)
    msg_b32 = encode_chat_id(graph_message_id)
    message = EmailMessage()
    message["From"] = f'"{from_name}" <{address}>'
    message["Reply-To"] = address
    message["To"] = "me@o365pop.local"
    message["Subject"] = f"Teams: {chat_subject}"
    message["Message-ID"] = f"<teams.{chat_b32}.{msg_b32}@{LOCAL_DOMAIN}>"
    message["X-O365POP-Source"] = "teams"
    message["X-O365POP-Chat-Id"] = chat_id
    message["X-O365POP-Message-Id"] = graph_message_id
    _attach_body(message, body, body_content_type)
    logger.info("tosser.mime_factory.teams_to_rfc822 | exit | message_id=%s", message["Message-ID"])
    return message


def _attach_body(message: EmailMessage, body: str, body_content_type: str) -> None:
    """Attach plain text, or multipart/alternative when the body is HTML.

    :param message: RFC822 being built. Example: ``EmailMessage()``
    :param body: Graph content. Example: ``"<p>Ship it</p>"``
    :param body_content_type: Graph contentType. Example: ``"html"``
    :return: None
    """
    if _is_html_body(body, body_content_type):
        message.set_content(_html_to_plain(body))
        message.add_alternative(_as_html_document(body), subtype="html")
        logger.info("tosser.mime_factory._attach_body | branch | body_type=html alternative=true")
        return
    message.set_content(body)
    logger.info("tosser.mime_factory._attach_body | branch | body_type=text")


def _is_html_body(body: str, body_content_type: str) -> bool:
    """True when Graph says html or the payload looks like markup.

    :param body: Graph content. Example: ``"<p>Ship it</p>"``
    :param body_content_type: Graph contentType. Example: ``"html"``
    :return: Whether to emit text/html. Example: ``True``
    """
    if body_content_type.lower() == "html":
        return True
    head = body.lstrip()[:200].lower()
    return any(marker in head for marker in _HTML_MARKERS)


def _as_html_document(fragment: str) -> str:
    """Wrap a Graph HTML fragment so Entourage 2008 can render it.

    :param fragment: Graph HTML. Example: ``"<p>Ship it</p>"``
    :return: Full HTML document. Example: ``"<html><body><p>Ship it</p></body></html>"``
    """
    if "<html" in fragment.lower():
        return fragment
    return f"<html><body>{fragment}</body></html>"


def _html_to_plain(markup: str) -> str:
    """Strip tags and unescape entities for the text/plain alternative.

    :param markup: Graph HTML. Example: ``"<p>Thank you&nbsp;!</p>"``
    :return: Readable plain text. Example: ``"Thank you !"``
    """
    parser = _PlainExtractor()
    parser.feed(markup)
    parser.close()
    text = unescape("".join(parser.parts)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


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
