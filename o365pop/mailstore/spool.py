"""Outbound spool new/retry/sent/failed."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SPOOL_DIRS = ("new", "retry", "sent", "failed")


class SpoolStore:
    """Filesystem outbound queue.

    :param root: Spool root. Example: ``Path("var/spool")``
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def enqueue(self, rfc822: bytes) -> Path:
        """Write a message into new/.

        :param rfc822: RFC822 bytes. Example: ``b"Subject: Hello Ada\\r\\n"``
        :return: Path in new/. Example: ``Path("var/spool/new/1.eml")``
        """
        logger.info("SpoolStore.enqueue | entry | size=%s", len(rfc822))
        raise NotImplementedError()

    def list_new(self) -> list[Path]:
        """Paths in new/ then retry/.

        :return: Files to scan. Example: ``[Path("var/spool/new/1.eml")]``
        """
        logger.info("SpoolStore.list_new | entry")
        raise NotImplementedError()

    def move_to(self, path: Path, bucket: str) -> Path:
        """Move a file to sent/retry/failed.

        :param path: Current file. Example: ``Path("var/spool/new/1.eml")``
        :param bucket: Target dir. Example: ``"sent"``
        :return: New path. Example: ``Path("var/spool/sent/1.eml")``
        :raises ValueError: if bucket unknown
        """
        logger.info("SpoolStore.move_to | entry | path=%s bucket=%s", path, bucket)
        raise NotImplementedError()

    def increment_attempts(self, path: Path) -> int:
        """Bump retry count for a file.

        :param path: Spool file. Example: ``Path("var/spool/retry/1.eml")``
        :return: New attempt count. Example: ``2``
        """
        logger.info("SpoolStore.increment_attempts | entry | path=%s", path)
        raise NotImplementedError()
