"""Scan spool: send_mime or post_chat_message; move file."""

from __future__ import annotations

import email
import logging
import sqlite3
from email import policy
from email.message import EmailMessage
from pathlib import Path

from o365pop.graph.port import GraphPort
from o365pop.mailstore.spool import SpoolStore
from o365pop.tosser.inbound import subject_of
from o365pop.tosser.outbound_router import OutboundRouter, Route
from o365pop.tosser.reply_text import extract

logger = logging.getLogger(__name__)

DEFAULT_RETRY_LIMIT = 3


class OutboundScanner:
    """One scan pass over new/retry.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param spool: Spool store. Example: ``SpoolStore(Path("var/spool"))``
    :param graph: Graph port. Example: ``FileGraphAdapter(case_dir)``
    :param retry_limit: Fail after N attempts. Example: ``3``
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        spool: SpoolStore,
        graph: GraphPort,
        retry_limit: int = DEFAULT_RETRY_LIMIT,
    ) -> None:
        self._conn = conn
        self._spool = spool
        self._graph = graph
        self._retry_limit = retry_limit

    def scan_once(self) -> dict[str, int]:
        """Process each queued file.

        :return: Counts. Example: ``{"sent": 1, "failed": 0}``
        """
        logger.info("OutboundScanner.scan_once | entry")
        sent = 0
        failed = 0
        for path in self._spool.list_new():
            outcome = self._send_then_archive(path)
            if outcome == "sent":
                sent += 1
            elif outcome == "failed":
                failed += 1
        logger.info("OutboundScanner.scan_once | exit | sent=%s failed=%s", sent, failed)
        return {"sent": sent, "failed": failed}

    def _send_then_archive(self, path: Path) -> str:
        """Route one RFC822 to chat post or sendMail, then archive.

        :param path: Queued eml. Example: ``Path("var/spool/new/1.eml")``
        :return: Outcome bucket. Example: ``"sent"``
        """
        rfc822 = path.read_bytes()
        subject = subject_of(rfc822)
        logger.info(
            "OutboundScanner.scan_once | processing | size=%s subject=%s",
            len(rfc822),
            subject,
        )
        message = email.message_from_bytes(rfc822, policy=policy.default)
        route = OutboundRouter(self._conn).route(message)
        if route.kind == "map_miss":
            return self._park_map_miss(path, subject)
        try:
            self._deliver(route, message, rfc822)
        except Exception as exc:
            return self._park_after_send_fail(path, subject, exc)
        dest = self._spool.move_to(path, "sent")
        logger.info("OutboundScanner.scan_once | branch | dest=%s bucket=sent", dest.name)
        return "sent"

    def _deliver(self, route: Route, message: EmailMessage, rfc822: bytes) -> None:
        """POST chat text or sendMail MIME.

        :param route: Router decision. Example: ``Route(kind="teams_chat", chat_id="19:general")``
        :param message: Parsed RFC822. Example: reply with body ``On it``
        :param rfc822: Raw bytes. Example: ``b"Subject: Hello Ada\\r\\n..."``
        :return: None
        :raises ValueError: if teams_chat is missing chat_id
        """
        if route.kind == "teams_chat":
            if not route.chat_id:
                raise ValueError("teams_chat route missing chat_id")
            text = extract(_plain_body(message))
            logger.info(
                "OutboundScanner.scan_once | processing | action=post_chat chat_id=%s text_len=%s",
                route.chat_id,
                len(text),
            )
            self._graph.post_chat_message(route.chat_id, text)
            return
        logger.info("OutboundScanner.scan_once | processing | action=send_mime size=%s", len(rfc822))
        self._graph.send_mime(rfc822)

    def _park_map_miss(self, path: Path, subject: str) -> str:
        """Park an unmapped @o365pop.local address without calling Graph.

        :param path: Queued eml. Example: ``Path("var/spool/new/1.eml")``
        :param subject: Message subject. Example: ``"Orphan reply"``
        :return: Outcome bucket. Example: ``"retry"``
        """
        return self._park(path, subject, reason="teams_map_miss")

    def _park_after_send_fail(self, path: Path, subject: str, exc: Exception) -> str:
        """Increment attempts and move the file to retry/ or failed/.

        :param path: Queued eml. Example: ``Path("var/spool/new/1.eml")``
        :param subject: Message subject. Example: ``"Hello Ada"``
        :param exc: send_mime failure. Example: ``httpx.HTTPStatusError(...)``
        :return: Outcome bucket. Example: ``"failed"``
        """
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return self._park(
            path,
            subject,
            reason="send_failed",
            status=status,
            err_type=type(exc).__name__,
        )

    def _park(
        self,
        path: Path,
        subject: str,
        reason: str,
        status: int | None = None,
        err_type: str | None = None,
    ) -> str:
        """Move to retry/ or failed/ after incrementing attempts.

        :param path: Queued eml. Example: ``Path("var/spool/new/1.eml")``
        :param subject: Message subject. Example: ``"Hello Ada"``
        :param reason: Error token. Example: ``"teams_map_miss"``
        :param status: HTTP status if any. Example: ``400``
        :param err_type: Exception class name. Example: ``"HTTPStatusError"``
        :return: Outcome bucket. Example: ``"failed"``
        """
        attempts = self._spool.increment_attempts(path)
        bucket = "failed" if attempts >= self._retry_limit else "retry"
        dest = self._spool.move_to(path, bucket)
        logger.error(
            "OutboundScanner.scan_once | error | reason=%s attempts=%s "
            "status=%s err_type=%s subject=%s dest=%s bucket=%s",
            reason,
            attempts,
            status,
            err_type,
            subject,
            dest.name,
            bucket,
        )
        logger.info("OutboundScanner.scan_once | branch | dest=%s bucket=%s", dest.name, bucket)
        return bucket


def _plain_body(message: EmailMessage) -> str:
    """Best-effort text/plain body.

    :param message: Parsed RFC822. Example: reply starting with ``On it``
    :return: Body text. Example: ``"On it\\n"``
    """
    part = message.get_body(preferencelist=("plain",))
    if part is None:
        return ""
    content = part.get_content()
    return content if isinstance(content, str) else ""
