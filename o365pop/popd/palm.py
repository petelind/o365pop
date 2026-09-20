"""Palm-safe rewrite of tossed RFC822 for the VersaMail POP view."""

from __future__ import annotations

import hashlib
import json
import logging
import textwrap
from datetime import UTC, datetime, timedelta
from email import message_from_bytes, policy
from email.message import EmailMessage, Message
from email.utils import format_datetime, parsedate_to_datetime
from io import BytesIO
from pathlib import Path

from twisted.mail.pop3 import IMailbox
from zope.interface import implementer

from o365pop.mailstore.maildir import MaildirStore
from o365pop.tosser.mime_factory import _html_to_plain

logger = logging.getLogger(__name__)

PALM_UIDL_MAX = 70
PALM_MAX_BYTES = 5 * 1024
PALM_WINDOW = timedelta(hours=24)
_PALM_DELETED = "palm-deleted.json"
_HEADER_BUDGET = 400
_LINE_WIDTH = 78


def hash_palm_uidl(store_uidl: str) -> str:
    """Stable UIDL hash (never the Graph id).

    :param store_uidl: Maildir UIDL. Example: ``"uid-outlook-AAMk-long-id"``
    :return: 64-char hex digest. Example: ``"2c26b46b68ffc68f..."``
    """
    digest = hashlib.sha256(store_uidl.encode("utf-8")).hexdigest()
    logger.info("popd.palm.hash_palm_uidl | exit | chars=%s", len(digest))
    return digest


def rewrite_palm_rfc822(raw: bytes, *, now: datetime | None = None) -> bytes | None:
    """Rewrite one message to Palm-safe text/plain, or drop it.

    :param raw: Original RFC822. Example: ``b"Content-Type: multipart/..."``
    :param now: Clock for the 24h window. Example: ``datetime(2026, 9, 20, tzinfo=UTC)``
    :return: Rewritten bytes, or None if too old / still too large. Example: ``b"Date: ..."``
    """
    clock = now or datetime.now(UTC)
    parsed = message_from_bytes(raw)
    when = _message_when(parsed, clock)
    if when < clock - PALM_WINDOW:
        logger.info("popd.palm.rewrite_palm_rfc822 | branch | skipped=true reason=too_old")
        return None
    rewritten = _build_plain(parsed, when)
    if len(rewritten) > PALM_MAX_BYTES:
        rewritten = _build_plain(parsed, when, max_body=PALM_MAX_BYTES - _HEADER_BUDGET)
    if len(rewritten) > PALM_MAX_BYTES:
        logger.info("popd.palm.rewrite_palm_rfc822 | branch | skipped=true reason=too_large")
        return None
    logger.info("popd.palm.rewrite_palm_rfc822 | exit | size=%s", len(rewritten))
    return rewritten


def list_palm_messages(
    store: MaildirStore,
    *,
    now: datetime | None = None,
    hidden: set[str] | None = None,
) -> list[tuple[str, str, bytes]]:
    """Filter maildir into Palm-safe (store_uidl, palm_uidl, rfc822) rows.

    :param store: Shared maildir. Example: ``MaildirStore(Path("var/maildir"))``
    :param now: Clock for the 24h window. Example: ``datetime(2026, 9, 20, tzinfo=UTC)``
    :param hidden: Already-deleted Palm UIDLs. Example: ``{"2c26b46b..."}``
    :return: Visible rows. Example: ``[("uid-outlook-1", "2c26...", b"Date: ...")]``
    """
    clock = now or datetime.now(UTC)
    skip = hidden or set()
    rows: list[tuple[str, str, bytes]] = []
    dropped = 0
    for store_uidl, _size in store.list_uidls():
        palm_id = hash_palm_uidl(store_uidl)
        rewritten = None if palm_id in skip else rewrite_palm_rfc822(store.get(store_uidl), now=clock)
        if rewritten is None:
            dropped += 1
            continue
        rows.append((store_uidl, palm_id, rewritten))
    logger.info("popd.palm.list_palm_messages | exit | count=%s dropped=%s", len(rows), dropped)
    return rows


def load_hidden_uidls(root: Path) -> set[str]:
    """Load Palm UIDLs hidden by a prior DELE.

    :param root: Maildir root. Example: ``Path("var/maildir")``
    :return: Hidden hashes. Example: ``{"2c26b46b68ffc68f"}``
    """
    path = root / _PALM_DELETED
    if not path.is_file():
        logger.info("popd.palm.load_hidden_uidls | exit | count=0")
        return set()
    payload = json.loads(path.read_text())
    hidden = {str(item) for item in payload}
    logger.info("popd.palm.load_hidden_uidls | exit | count=%s", len(hidden))
    return hidden


def save_hidden_uidls(root: Path, hidden: set[str]) -> None:
    """Persist Palm UIDLs hidden by DELE (maildir files stay).

    :param root: Maildir root. Example: ``Path("var/maildir")``
    :param hidden: Hidden hashes. Example: ``{"2c26b46b68ffc68f"}``
    :return: None
    """
    (root / _PALM_DELETED).write_text(json.dumps(sorted(hidden)))
    logger.info("popd.palm.save_hidden_uidls | exit | count=%s", len(hidden))


@implementer(IMailbox)
class PalmSafeMailbox:
    """POP view: hashed UIDL, 24h window, 7-bit text. DELE does not touch maildir."""

    def __init__(self, store: MaildirStore, *, now: datetime | None = None) -> None:
        self._store = store
        self._hidden = load_hidden_uidls(store.root)
        self._messages = list_palm_messages(store, now=now, hidden=self._hidden)
        self._deleted: set[int] = set()
        logger.info("popd.palm.PalmSafeMailbox.__init__ | config | count=%s", len(self._messages))

    def listMessages(self, index: int | None = None) -> int | list[int]:
        """Rewritten sizes, 0-based index.

        :param index: Message index or None. Example: ``0``
        :return: Size or list of sizes. Example: ``[240]``
        """
        sizes = [0 if i in self._deleted else len(rfc) for i, (_s, _p, rfc) in enumerate(self._messages)]
        if index is None:
            logger.info("popd.palm.PalmSafeMailbox.listMessages | exit | count=%s", len(sizes))
            return sizes
        if index < 0 or index >= len(sizes):
            raise ValueError(index)
        logger.info("popd.palm.PalmSafeMailbox.listMessages | exit | size=%s", sizes[index])
        return sizes[index]

    def getMessage(self, index: int):
        """File-like rewritten RFC822 for RETR.

        :param index: 0-based. Example: ``0``
        :return: File object. Example: ``BytesIO(b"Subject: ...")``
        """
        _store_uidl, palm_uidl, data = self._row_at(index)
        logger.info("popd.palm.PalmSafeMailbox.getMessage | exit | uidl=%s size=%s", palm_uidl, len(data))
        return BytesIO(data)

    def getUidl(self, index: int) -> bytes:
        """Hashed UIDL bytes (≤70 chars).

        :param index: 0-based. Example: ``0``
        :return: UIDL. Example: ``b"2c26b46b68ffc68f..."``
        """
        _store_uidl, palm_uidl, _data = self._row_at(index)
        logger.info("popd.palm.PalmSafeMailbox.getUidl | exit | uidl=%s chars=%s", palm_uidl, len(palm_uidl))
        return palm_uidl.encode("ascii")

    def deleteMessage(self, index: int) -> None:
        """Mark Palm hide (does not delete the maildir file).

        :param index: 0-based. Example: ``0``
        :return: None
        """
        self._row_at(index)
        self._deleted.add(index)
        logger.info("popd.palm.PalmSafeMailbox.deleteMessage | exit | marked=true index=%s", index)

    def undeleteMessages(self) -> None:
        """Undo DELE in this session.

        :return: None
        """
        self._deleted.clear()
        logger.info("popd.palm.PalmSafeMailbox.undeleteMessages | exit | cleared=true")

    def sync(self) -> None:
        """Persist Palm hides. Do not delete maildir or TossedMessage.

        :return: None
        """
        for index in sorted(self._deleted):
            self._hidden.add(self._messages[index][1])
        save_hidden_uidls(self._store.root, self._hidden)
        self._deleted.clear()
        logger.info("popd.palm.PalmSafeMailbox.sync | exit | hidden=%s", len(self._hidden))

    def _row_at(self, index: int) -> tuple[str, str, bytes]:
        """Live (not deleted) Palm row.

        :param index: 0-based. Example: ``0``
        :return: store UIDL, Palm UIDL, rewritten bytes. Example: ``("uid-outlook-1", "2c26...", b"Date:")``
        :raises ValueError: if index is out of range or deleted
        """
        if index < 0 or index >= len(self._messages) or index in self._deleted:
            raise ValueError(index)
        return self._messages[index]


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
    """Build a 7-bit text/plain RFC822 with folded headers and CRLF.

    :param parsed: Source message. Example: ``message_from_bytes(raw)``
    :param when: Date to stamp. Example: ``datetime(2026, 9, 20, tzinfo=UTC)``
    :param max_body: Optional body cap. Example: ``4720``
    :return: SMTP-serialized bytes. Example: ``b"Date: Sat, 20 Sep 2026..."``
    """
    body = _seven_bit(_wrap_lines(_plain_body(parsed)))
    if max_body is not None:
        body = body[: max(0, max_body)]
    msg = EmailMessage(policy=policy.SMTP)
    msg["From"] = _ascii_header(parsed.get("From"), "unknown@o365pop.local")
    msg["To"] = _ascii_header(parsed.get("To"), "me@o365pop.local")
    msg["Subject"] = _ascii_header(parsed.get("Subject"), "(no subject)")
    msg["Date"] = format_datetime(when)
    _copy_optional_header(msg, parsed, "Message-ID")
    _copy_optional_header(msg, parsed, "Reply-To")
    msg.set_content(body, subtype="plain", charset="us-ascii", cte="7bit")
    return msg.as_bytes()


def _plain_body(parsed: Message) -> str:
    """Prefer text/plain; else strip HTML; never keep multipart.

    :param parsed: Source message. Example: ``message_from_bytes(raw)``
    :return: Visible text. Example: ``"Ship it"``
    """
    text = _first_part(parsed, "text/plain")
    if text:
        return text
    html = _first_part(parsed, "text/html")
    if html:
        return _html_to_plain(html)
    if parsed.is_multipart():
        return ""
    payload = _decode_payload(parsed)
    if parsed.get_content_type() == "text/html":
        return _html_to_plain(payload)
    return payload


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
    """Force a header to 7-bit ASCII.

    :param value: Original header. Example: ``"Ada <ada@example.com>"``
    :param fallback: Used when empty. Example: ``"unknown@o365pop.local"``
    :return: ASCII text. Example: ``"Ada <ada@example.com>"``
    """
    if not value:
        return fallback
    return str(value).encode("ascii", "replace").decode("ascii")


def _copy_optional_header(dest: EmailMessage, source: Message, name: str) -> None:
    """Copy one header when present.

    :param dest: Message being built. Example: ``EmailMessage()``
    :param source: Original. Example: ``message_from_bytes(raw)``
    :param name: Header name. Example: ``"Reply-To"``
    :return: None
    """
    value = source.get(name)
    if value:
        dest[name] = _ascii_header(str(value), "")


def _seven_bit(text: str) -> str:
    """Replace non-ASCII so CTE 7bit is legal.

    :param text: Body. Example: ``"café"``
    :return: ASCII. Example: ``"caf?"``
    """
    return text.encode("ascii", "replace").decode("ascii")


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
