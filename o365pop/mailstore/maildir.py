"""Inbound maildir (stdlib mailbox.Maildir)."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class MaildirStore:
    """Add/list/get/delete RFC822 files.

    :param root: Maildir root. Example: ``Path("var/maildir")``
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def add(self, rfc822: bytes, uidl: str) -> str:
        """Drop a message and return its key.

        :param rfc822: RFC822 bytes. Example: ``b"Subject: Q3 close\\r\\n"``
        :param uidl: Stable UIDL. Example: ``"uid-outlook-1"``
        :return: Maildir key. Example: ``"1234567890.M123P1"``
        """
        logger.info("MaildirStore.add | entry | uidl=%s size=%s", uidl, len(rfc822))
        raise NotImplementedError()

    def list_uidls(self) -> list[tuple[str, int]]:
        """UIDL and size for each message.

        :return: Pairs. Example: ``[("uid-outlook-1", 240)]``
        """
        logger.info("MaildirStore.list_uidls | entry")
        raise NotImplementedError()

    def get(self, uidl: str) -> bytes:
        """Read RFC822 by UIDL.

        :param uidl: UIDL. Example: ``"uid-outlook-1"``
        :return: Bytes. Example: ``b"Subject: Q3 close\\r\\n"``
        :raises KeyError: if missing
        """
        logger.info("MaildirStore.get | entry | uidl=%s", uidl)
        raise NotImplementedError()

    def delete(self, uidl: str) -> None:
        """Remove the local file only.

        :param uidl: UIDL. Example: ``"uid-outlook-1"``
        :return: None
        """
        logger.info("MaildirStore.delete | entry | uidl=%s", uidl)
        raise NotImplementedError()
