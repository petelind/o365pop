"""Scan spool: send_mime or post_chat_message; move file."""

from __future__ import annotations

import logging
import sqlite3

from o365pop.graph.port import GraphPort
from o365pop.mailstore.spool import SpoolStore

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
        # 1. list_new
        # 2. OutboundRouter.route
        # 3. send_mime or post_chat_message or fail-closed
        # 4. move sent/retry/failed
        raise NotImplementedError()
