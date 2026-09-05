"""Scan spool: send_mime or post_chat_message; move file."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from o365pop.graph.port import GraphPort
from o365pop.mailstore.spool import SpoolStore
from o365pop.tosser.inbound import subject_of

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
            self._send_then_archive(path)
            sent += 1
        logger.info("OutboundScanner.scan_once | exit | sent=%s failed=%s", sent, failed)
        return {"sent": sent, "failed": failed}

    def _send_then_archive(self, path: Path) -> None:
        """POST MIME via sendMail and move the file to sent/.

        :param path: Queued eml. Example: ``Path("var/spool/new/1.eml")``
        :return: None
        """
        rfc822 = path.read_bytes()
        subject = subject_of(rfc822)
        logger.info(
            "OutboundScanner.scan_once | processing | size=%s subject=%s",
            len(rfc822),
            subject,
        )
        self._graph.send_mime(rfc822)
        dest = self._spool.move_to(path, "sent")
        logger.info("OutboundScanner.scan_once | branch | dest=%s bucket=sent", dest.name)
