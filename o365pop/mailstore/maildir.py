"""Inbound maildir (stdlib mailbox.Maildir)."""

from __future__ import annotations

import json
import logging
import mailbox
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_UIDL_MAP = "uidl.json"


class MaildirStore:
    """Add/list/get/delete RFC822 files.

    :param root: Maildir root. Example: ``Path("var/maildir")``
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        self._box = mailbox.Maildir(str(root), create=True)

    @property
    def root(self) -> Path:
        """Maildir root on disk.

        :return: Root path. Example: ``Path("var/maildir")``
        """
        return self._root

    def add(self, rfc822: bytes, uidl: str) -> str:
        """Drop a message and return its key.

        :param rfc822: RFC822 bytes. Example: ``b"Subject: Q3 close\\r\\n"``
        :param uidl: Stable UIDL. Example: ``"uid-outlook-1"``
        :return: Maildir key. Example: ``"1234567890.M123P1"``
        """
        logger.info("MaildirStore.add | entry | uidl=%s size=%s", uidl, len(rfc822))
        key = self._box.add(rfc822)
        mapping = self._load_uidls()
        mapping[uidl] = key
        self._save_uidls(mapping)
        logger.info("MaildirStore.add | exit | uidl=%s key=%s", uidl, key)
        return key

    def iter_uidls(self) -> list[str]:
        """UIDLs that still have a file.

        :return: UIDL strings. Example: ``["uid-outlook-1"]``
        """
        mapping = self._load_uidls()
        return [uidl for uidl, key in mapping.items() if key in self._box]

    def peek(self, uidl: str, limit: int = 4096) -> bytes:
        """Read the first bytes of a message (headers).

        :param uidl: UIDL. Example: ``"uid-outlook-1"``
        :param limit: Max bytes. Example: ``4096``
        :return: Prefix. Example: ``b"Date: Sat, 20 Sep 2026..."``
        :raises KeyError: if missing
        """
        handle = self._box.get_file(self._key(uidl))
        try:
            return handle.read(limit)
        finally:
            handle.close()

    def mtime(self, uidl: str) -> datetime:
        """Filesystem mtime for a stored message.

        :param uidl: UIDL. Example: ``"uid-outlook-1"``
        :return: Aware UTC time. Example: ``datetime(2026, 9, 20, tzinfo=UTC)``
        :raises KeyError: if missing
        """
        key = self._key(uidl)
        path = Path(self._box._path) / self._box._lookup(key)
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)

    def _key(self, uidl: str) -> str:
        """Maildir key for a UIDL.

        :param uidl: UIDL. Example: ``"uid-outlook-1"``
        :return: Key. Example: ``"1234567890.M123P1"``
        :raises KeyError: if missing
        """
        key = self._load_uidls().get(uidl)
        if key is None or key not in self._box:
            raise KeyError(uidl)
        return key

    def list_uidls(self) -> list[tuple[str, int]]:
        """UIDL and size for each message.

        :return: Pairs. Example: ``[("uid-outlook-1", 240)]``
        """
        logger.info("MaildirStore.list_uidls | entry")
        mapping = self._load_uidls()
        pairs = [(uidl, len(self._box[key])) for uidl, key in mapping.items() if key in self._box]
        logger.info("MaildirStore.list_uidls | exit | count=%s", len(pairs))
        return pairs

    def get(self, uidl: str) -> bytes:
        """Read RFC822 by UIDL.

        :param uidl: UIDL. Example: ``"uid-outlook-1"``
        :return: Bytes. Example: ``b"Subject: Q3 close\\r\\n"``
        :raises KeyError: if missing
        """
        logger.info("MaildirStore.get | entry | uidl=%s", uidl)
        key = self._load_uidls().get(uidl)
        if key is None or key not in self._box:
            raise KeyError(uidl)
        data = bytes(self._box[key])
        logger.info("MaildirStore.get | exit | uidl=%s size=%s", uidl, len(data))
        return data

    def delete(self, uidl: str) -> None:
        """Remove the local file only.

        :param uidl: UIDL. Example: ``"uid-outlook-1"``
        :return: None
        """
        logger.info("MaildirStore.delete | entry | uidl=%s", uidl)
        mapping = self._load_uidls()
        key = mapping.pop(uidl, None)
        if key is not None and key in self._box:
            del self._box[key]
        self._save_uidls(mapping)
        logger.info("MaildirStore.delete | exit | uidl=%s", uidl)

    def _load_uidls(self) -> dict[str, str]:
        """Read uidl → maildir key map.

        :return: Mapping. Example: ``{"uid-outlook-1": "1234.M1"}``
        """
        path = self._root / _UIDL_MAP
        if not path.is_file():
            return {}
        payload = json.loads(path.read_text())
        return {str(key): str(value) for key, value in payload.items()}

    def _save_uidls(self, mapping: dict[str, str]) -> None:
        """Persist uidl map.

        :param mapping: uidl → key. Example: ``{"uid-outlook-1": "1234.M1"}``
        :return: None
        """
        (self._root / _UIDL_MAP).write_text(json.dumps(mapping))
