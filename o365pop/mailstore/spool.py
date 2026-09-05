"""Outbound spool new/retry/sent/failed."""

from __future__ import annotations

import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

SPOOL_DIRS = ("new", "retry", "sent", "failed")
_ATTEMPTS_SUFFIX = ".attempts"


class SpoolStore:
    """Filesystem outbound queue.

    :param root: Spool root. Example: ``Path("var/spool")``
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        for name in SPOOL_DIRS:
            (self._root / name).mkdir(parents=True, exist_ok=True)
        logger.info("SpoolStore.__init__ | config | root=%s", self._root)

    def enqueue(self, rfc822: bytes) -> Path:
        """Write a message into new/.

        :param rfc822: RFC822 bytes. Example: ``b"Subject: Hello Ada\\r\\n"``
        :return: Path in new/. Example: ``Path("var/spool/new/1.eml")``
        """
        logger.info("SpoolStore.enqueue | entry | size=%s", len(rfc822))
        path = self._root / "new" / f"{time.time_ns()}.eml"
        path.write_bytes(rfc822)
        logger.info("SpoolStore.enqueue | exit | path=%s", path.name)
        return path

    def list_new(self) -> list[Path]:
        """Paths in new/ then retry/.

        :return: Files to scan. Example: ``[Path("var/spool/new/1.eml")]``
        """
        logger.info("SpoolStore.list_new | entry")
        files = _eml_in(self._root / "new") + _eml_in(self._root / "retry")
        logger.info("SpoolStore.list_new | exit | count=%s", len(files))
        return files

    def move_to(self, path: Path, bucket: str) -> Path:
        """Move a file to sent/retry/failed.

        :param path: Current file. Example: ``Path("var/spool/new/1.eml")``
        :param bucket: Target dir. Example: ``"sent"``
        :return: New path. Example: ``Path("var/spool/sent/1.eml")``
        :raises ValueError: if bucket unknown
        """
        logger.info("SpoolStore.move_to | entry | path=%s bucket=%s", path.name, bucket)
        if bucket not in SPOOL_DIRS:
            raise ValueError(f"unknown spool bucket: {bucket}")
        dest = self._root / bucket / path.name
        sidecar = _attempts_path(path)
        path.replace(dest)
        if sidecar.is_file():
            sidecar.replace(_attempts_path(dest))
        logger.info("SpoolStore.move_to | exit | dest=%s", dest)
        return dest

    def increment_attempts(self, path: Path) -> int:
        """Bump retry count for a file.

        :param path: Spool file. Example: ``Path("var/spool/retry/1.eml")``
        :return: New attempt count. Example: ``2``
        """
        logger.info("SpoolStore.increment_attempts | entry | path=%s", path.name)
        sidecar = _attempts_path(path)
        current = int(sidecar.read_text()) if sidecar.is_file() else 0
        nxt = current + 1
        sidecar.write_text(str(nxt))
        logger.info("SpoolStore.increment_attempts | exit | attempts=%s", nxt)
        return nxt


def _eml_in(directory: Path) -> list[Path]:
    """Sorted ``*.eml`` files in a bucket.

    :param directory: Bucket. Example: ``Path("var/spool/new")``
    :return: Files. Example: ``[Path("var/spool/new/1.eml")]``
    """
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.iterdir() if path.suffix == ".eml" and path.is_file())


def _attempts_path(path: Path) -> Path:
    """Sidecar next to an eml.

    :param path: Message path. Example: ``Path("var/spool/new/1.eml")``
    :return: Sidecar. Example: ``Path("var/spool/new/1.eml.attempts")``
    """
    return path.with_name(path.name + _ATTEMPTS_SUFFIX)
