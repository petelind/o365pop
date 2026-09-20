"""Palm-safe rewrite and incremental publish of var/maildir-palm."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import textwrap
from datetime import UTC, datetime, timedelta
from email import message_from_bytes
from email.message import Message
from email.utils import format_datetime, parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from o365pop.mailstore.maildir import MaildirStore

logger = logging.getLogger(__name__)

PALM_UIDL_MAX = 70
PALM_MAX_BYTES = 5 * 1024
PALM_WINDOW = timedelta(hours=24)
_PALM_DELETED = "palm-deleted.json"
_PALM_INDEX = "palm-index.json"
_HEADER_BUDGET = 400
_LINE_WIDTH = 78
_BLOCK_TAGS = frozenset({"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4"})
_STUB_PLAIN = ("please view", "html formatted", "this message is in html")


def hash_palm_uidl(store_uidl: str) -> str:
    """Stable UIDL hash (never the Graph id).

    :param store_uidl: Maildir UIDL. Example: ``"uid-outlook-AAMk-long-id"``
    :return: 64-char hex digest. Example: ``"2c26b46b68ffc68f..."``
    """
    digest = hashlib.sha256(store_uidl.encode("utf-8")).hexdigest()
    logger.debug("tosser.palm_view.hash_palm_uidl | exit | chars=%s", len(digest))
    return digest


def rewrite_palm_rfc822(
    raw: bytes,
    *,
    now: datetime | None = None,
    fallback_when: datetime | None = None,
) -> bytes | None:
    """Rewrite one message to Palm-safe flat text/plain, or drop it.

    :param raw: Original RFC822. Example: ``b"Content-Type: multipart/..."``
    :param now: Clock for the 24h window. Example: ``datetime(2026, 9, 20, tzinfo=UTC)``
    :param fallback_when: Used when Date is missing. Example: ``datetime(2026, 9, 19, tzinfo=UTC)``
    :return: Rewritten bytes, or None if too old / still too large. Example: ``b"Date: ..."``
    """
    clock = now or datetime.now(UTC)
    parsed = message_from_bytes(raw)
    when = _message_when(parsed, fallback_when or clock)
    if when < clock - PALM_WINDOW:
        logger.info("tosser.palm_view.rewrite_palm_rfc822 | branch | skipped=true reason=too_old")
        return None
    rewritten = _build_plain(parsed, when)
    if len(rewritten) > PALM_MAX_BYTES:
        rewritten = _build_plain(parsed, when, max_body=PALM_MAX_BYTES - _HEADER_BUDGET)
    if len(rewritten) > PALM_MAX_BYTES:
        logger.info("tosser.palm_view.rewrite_palm_rfc822 | branch | skipped=true reason=too_large")
        return None
    body = _body_after_headers(rewritten)
    logger.info(
        "tosser.palm_view.rewrite_palm_rfc822 | exit | size=%s body_len=%s",
        len(rewritten),
        len(body),
    )
    return rewritten


def publish_palm_view(
    source: MaildirStore,
    dest: MaildirStore,
    *,
    now: datetime | None = None,
) -> dict[str, int]:
    """Incrementally publish Palm-safe files into dest.

    :param source: Entourage maildir. Example: ``MaildirStore(Path("var/maildir"))``
    :param dest: Palm maildir. Example: ``MaildirStore(Path("var/maildir-palm"))``
    :param now: Clock for the 24h window. Example: ``datetime(2026, 9, 20, tzinfo=UTC)``
    :return: Counts. Example: ``{"written": 1, "reused": 0, "dropped": 2}``
    """
    clock = now or datetime.now(UTC)
    hidden = load_hidden_uidls(dest.root)
    index = _load_index(dest.root)
    written = reused = dropped = 0
    keep_store: set[str] = set()
    keep_palm: set[str] = set()
    for store_uidl, mtime, head in source.scan_heads():
        palm_id = hash_palm_uidl(store_uidl)
        stamp = mtime.isoformat()
        when = _message_when(message_from_bytes(head), mtime)
        if palm_id in hidden or when < clock - PALM_WINDOW:
            dropped += 1
            continue
        if _can_reuse(index, dest, store_uidl, palm_id, stamp):
            keep_store.add(store_uidl)
            keep_palm.add(palm_id)
            reused += 1
            continue
        rewritten = rewrite_palm_rfc822(
            source.read_bytes(store_uidl),
            now=clock,
            fallback_when=mtime,
        )
        if rewritten is None:
            dropped += 1
            continue
        _replace_dest(dest, palm_id, rewritten)
        index[store_uidl] = {"palm_uidl": palm_id, "source_mtime": stamp}
        keep_store.add(store_uidl)
        keep_palm.add(palm_id)
        written += 1
    dropped += _drop_stale(dest, index, keep_store, keep_palm)
    _save_index(dest.root, index)
    logger.info(
        "tosser.palm_view.publish | exit | written=%s reused=%s dropped=%s",
        written,
        reused,
        dropped,
    )
    return {"written": written, "reused": reused, "dropped": dropped}


def load_hidden_uidls(root: Path) -> set[str]:
    """Load Palm UIDLs hidden by a prior DELE.

    :param root: Palm maildir root. Example: ``Path("var/maildir-palm")``
    :return: Hidden hashes. Example: ``{"2c26b46b68ffc68f"}``
    """
    path = root / _PALM_DELETED
    if not path.is_file():
        logger.info("tosser.palm_view.load_hidden_uidls | exit | count=0")
        return set()
    hidden = {str(item) for item in json.loads(path.read_text())}
    logger.info("tosser.palm_view.load_hidden_uidls | exit | count=%s", len(hidden))
    return hidden


def save_hidden_uidls(root: Path, hidden: set[str]) -> None:
    """Persist Palm UIDLs hidden by DELE.

    :param root: Palm maildir root. Example: ``Path("var/maildir-palm")``
    :param hidden: Hidden hashes. Example: ``{"2c26b46b68ffc68f"}``
    :return: None
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / _PALM_DELETED).write_text(json.dumps(sorted(hidden)))
    logger.info("tosser.palm_view.save_hidden_uidls | exit | count=%s", len(hidden))


def _can_reuse(
    index: dict[str, Any],
    dest: MaildirStore,
    store_uidl: str,
    palm_id: str,
    stamp: str,
) -> bool:
    """True when dest already has this source mtime.

    :param index: Manifest. Example: ``{"uid-1": {"palm_uidl": "ab", "source_mtime": "..."}}``
    :param dest: Palm store. Example: ``MaildirStore(Path("var/maildir-palm"))``
    :param store_uidl: Source UIDL. Example: ``"uid-outlook-1"``
    :param palm_id: Hashed UIDL. Example: ``"2c26b46b..."``
    :param stamp: Source mtime iso. Example: ``"2026-09-20T16:00:00+00:00"``
    :return: Whether to skip rewrite. Example: ``True``
    """
    prev = index.get(store_uidl)
    if prev is None:
        return False
    if prev.get("source_mtime") != stamp or prev.get("palm_uidl") != palm_id:
        return False
    return palm_id in dest.iter_uidls()


def _replace_dest(dest: MaildirStore, palm_id: str, rewritten: bytes) -> None:
    """Write one Palm file, replacing a prior copy.

    :param dest: Palm store. Example: ``MaildirStore(Path("var/maildir-palm"))``
    :param palm_id: Hashed UIDL. Example: ``"2c26b46b..."``
    :param rewritten: Flat RFC822. Example: ``b"Date: ..."``
    :return: None
    """
    if palm_id in dest.iter_uidls():
        dest.delete(palm_id)
    dest.add(rewritten, palm_id)


def _drop_stale(
    dest: MaildirStore,
    index: dict[str, Any],
    keep_store: set[str],
    keep_palm: set[str],
) -> int:
    """Remove dest rows that aged out, vanished, or are hidden.

    :param dest: Palm store. Example: ``MaildirStore(Path("var/maildir-palm"))``
    :param index: Manifest (mutated). Example: ``{}``
    :param keep_store: Source UIDLs still visible. Example: ``{"uid-outlook-1"}``
    :param keep_palm: Palm UIDLs still visible. Example: ``{"2c26b46b..."}``
    :return: Dropped dest count. Example: ``2``
    """
    dropped = 0
    for uidl, _size in list(dest.list_uidls()):
        if uidl in keep_palm:
            continue
        dest.delete(uidl)
        dropped += 1
    for store_uidl in [key for key in index if key not in keep_store]:
        del index[store_uidl]
    return dropped


def _load_index(root: Path) -> dict[str, Any]:
    """Read store_uidl → {palm_uidl, source_mtime}.

    :param root: Palm maildir root. Example: ``Path("var/maildir-palm")``
    :return: Manifest. Example: ``{"uid-outlook-1": {"palm_uidl": "ab", "source_mtime": "..."}}``
    """
    path = root / _PALM_INDEX
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text())
    return {str(key): dict(value) for key, value in payload.items()}


def _save_index(root: Path, index: dict[str, Any]) -> None:
    """Persist the Palm publish manifest.

    :param root: Palm maildir root. Example: ``Path("var/maildir-palm")``
    :param index: Manifest. Example: ``{"uid-outlook-1": {"palm_uidl": "ab", "source_mtime": "..."}}``
    :return: None
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / _PALM_INDEX).write_text(json.dumps(index, indent=2, sort_keys=True))


def _message_when(parsed: Message, fallback: datetime) -> datetime:
    """Parse Date, or fall back so missing Date still appears in the window.

    :param parsed: RFC822 message. Example: ``message_from_bytes(raw)``
    :param fallback: Clock when Date is absent. Example: ``datetime(2026, 9, 20, tzinfo=UTC)``
    :return: Aware UTC datetime. Example: ``datetime(2026, 9, 20, 16, 0, tzinfo=UTC)``
    """
    raw = parsed.get("Date")
    if not raw:
        return fallback
    try:
        when = parsedate_to_datetime(str(raw))
    except (TypeError, ValueError, IndexError):
        return fallback
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return when.astimezone(UTC)


def _build_plain(parsed: Message, when: datetime, *, max_body: int | None = None) -> bytes:
    """Build a flat 7-bit text/plain RFC822 (no MIME-Version).

    :param parsed: Source message. Example: ``message_from_bytes(raw)``
    :param when: Date to stamp. Example: ``datetime(2026, 9, 20, tzinfo=UTC)``
    :param max_body: Optional body cap. Example: ``4720``
    :return: SMTP-serialized bytes. Example: ``b"Date: Sat, 20 Sep 2026..."``
    """
    body = _seven_bit(_wrap_lines(_plain_body(parsed)))
    if max_body is not None:
        body = body[: max(0, max_body)]
    if not body.strip():
        body = "(no text)"
    headers = [
        ("From", _ascii_header(parsed.get("From"), "unknown@o365pop.local")),
        ("To", _ascii_header(parsed.get("To"), "me@o365pop.local")),
        ("Subject", _ascii_header(parsed.get("Subject"), "(no subject)")),
        ("Date", format_datetime(when)),
        ("Content-Type", "text/plain; charset=us-ascii"),
        ("Content-Transfer-Encoding", "7bit"),
    ]
    for name in ("Message-ID", "Reply-To"):
        value = parsed.get(name)
        if value:
            headers.append((name, _ascii_header(str(value), "")))
    return _serialize_simple(headers, body)


def _plain_body(parsed: Message) -> str:
    """Prefer useful text/plain; else strip HTML. Ignore stub/blank parts.

    :param parsed: Source message. Example: ``message_from_bytes(raw)``
    :return: Visible text. Example: ``"Ship it"``
    """
    plain = _first_part(parsed, "text/plain").strip()
    html_text = _html_to_plain(_first_part(parsed, "text/html"))
    if html_text and _is_stub_plain(plain):
        logger.info("tosser.palm_view.rewrite_palm_rfc822 | branch | body_source=html")
        return html_text
    if plain:
        logger.info("tosser.palm_view.rewrite_palm_rfc822 | branch | body_source=plain")
        return plain
    if html_text:
        logger.info("tosser.palm_view.rewrite_palm_rfc822 | branch | body_source=html")
        return html_text
    payload = _decode_payload(parsed).strip()
    if parsed.get_content_type() == "text/html":
        return _html_to_plain(payload)
    return payload


def _is_stub_plain(text: str) -> bool:
    """True when text/plain is blank or an HTML-only placeholder.

    :param text: Decoded text/plain. Example: ``" "``
    :return: Whether to prefer HTML. Example: ``True``
    """
    if len(text) < 8:
        return True
    lowered = text.lower()
    return any(marker in lowered for marker in _STUB_PLAIN)


def _first_part(parsed: Message, content_type: str) -> str:
    """First matching body part, walking a multipart tree.

    :param parsed: Source message. Example: ``message_from_bytes(raw)``
    :param content_type: MIME type. Example: ``"text/plain"``
    :return: Decoded text or ``""``. Example: ``"Ship it"``
    """
    if parsed.get_content_type() == content_type and not parsed.is_multipart():
        return _decode_payload(parsed)
    for part in parsed.walk():
        if part.get_content_type() == content_type and not part.is_multipart():
            return _decode_payload(part)
    return ""


def _decode_payload(part: Message) -> str:
    """Decode a leaf part to text.

    :param part: MIME part. Example: ``parsed.get_payload()[0]``
    :return: Unicode text. Example: ``"Ship it"``
    """
    payload = part.get_payload(decode=True)
    if payload is None:
        raw = part.get_payload()
        return raw if isinstance(raw, str) else ""
    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _ascii_header(value: str | None, fallback: str) -> str:
    """Force a header to a single 7-bit ASCII line.

    :param value: Original header. Example: ``"Ada <ada@example.com>"``
    :param fallback: Used when empty. Example: ``"unknown@o365pop.local"``
    :return: ASCII text. Example: ``"Ada <ada@example.com>"``
    """
    if not value:
        return fallback
    flat = " ".join(str(value).split())
    return flat.encode("ascii", "replace").decode("ascii")


def _seven_bit(text: str) -> str:
    """Replace non-ASCII so CTE 7bit is legal.

    :param text: Body. Example: ``"café"``
    :return: ASCII. Example: ``"caf?"``
    """
    return text.encode("ascii", "replace").decode("ascii")


def _html_to_plain(markup: str) -> str:
    """Strip tags for the Palm text/plain body.

    :param markup: HTML. Example: ``"<p>Ship it</p>"``
    :return: Visible text. Example: ``"Ship it"``
    """
    if not markup:
        return ""
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


def _wrap_lines(text: str) -> str:
    """Fold long body lines to 78 characters.

    :param text: Body. Example: ``"x" * 200``
    :return: Wrapped text. Example: ``"xxxx\\nxxxx"``
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    wrapped: list[str] = []
    for line in lines:
        if len(line) <= _LINE_WIDTH:
            wrapped.append(line)
            continue
        wrapped.extend(textwrap.wrap(line, width=_LINE_WIDTH) or [""])
    return "\n".join(wrapped)


def _serialize_simple(headers: list[tuple[str, str]], body: str) -> bytes:
    """CRLF RFC822 without MIME-Version so VersaMail sees the body.

    :param headers: Name/value pairs. Example: ``[("Subject", "Q3")]``
    :param body: 7-bit text. Example: ``"Ship it"``
    :return: Bytes. Example: ``b"Subject: Q3\\r\\n\\r\\nShip it\\r\\n"``
    """
    lines: list[str] = []
    for name, value in headers:
        raw = f"{name}: {value}"
        if len(raw) <= _LINE_WIDTH:
            lines.append(raw)
            continue
        lines.extend(textwrap.wrap(raw, width=_LINE_WIDTH, subsequent_indent=" "))
    lines.append("")
    lines.extend(body.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
    text = "\r\n".join(lines)
    if not text.endswith("\r\n"):
        text += "\r\n"
    return text.encode("ascii", "replace")


def _body_after_headers(raw: bytes) -> bytes:
    """Bytes after the header blank line.

    :param raw: RFC822. Example: ``b"Subject: x\\r\\n\\r\\nHi\\r\\n"``
    :return: Body. Example: ``b"Hi\\r\\n"``
    """
    split = raw.split(b"\r\n\r\n", 1)
    return split[1] if len(split) == 2 else b""
