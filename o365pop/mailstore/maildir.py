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
        for folder in ("cur", "new", "tmp"):
            (self._root / folder).mkdir(exist_ok=True)

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
        return [uidl for uidl in self._load_uidls() if self.has_uidl(uidl)]

    def has_uidl(self, uidl: str) -> bool:
        """True when uidl.json points at a file in new/ or cur/.

        :param uidl: UIDL. Example: ``"uid-outlook-1"``
        :return: Whether the file exists. Example: ``True``
        """
        key = self._load_uidls().get(uidl)
        return bool(key) and self._file_path(key) is not None

    def scan_heads(self, limit: int = 2048) -> list[tuple[str, datetime, bytes]]:
        """UIDL, mtime, and header prefix without refreshing the Maildir TOC.

        :param limit: Header bytes per file. Example: ``2048``
        :return: Rows. Example: ``[("uid-outlook-1", datetime(2026, 9, 20, tzinfo=UTC), b"Date: ...")]``
        """
        rows: list[tuple[str, datetime, bytes]] = []
        for uidl, key in self._load_uidls().items():
            path = self._file_path(key)
            if path is None:
                continue
            stat = path.stat()
            with path.open("rb") as handle:
                head = handle.read(limit)
            rows.append((uidl, datetime.fromtimestamp(stat.st_mtime, tz=UTC), head))
        logger.info("MaildirStore.scan_heads | exit | count=%s", len(rows))
        return rows

    def read_bytes(self, uidl: str) -> bytes:
        """Read a full RFC822 via the uidl map (no Maildir TOC refresh).

        :param uidl: UIDL. Example: ``"uid-outlook-1"``
        :return: Bytes. Example: ``b"Subject: Q3 close\\r\\n"``
        :raises KeyError: if missing
        """
        path = self._file_path(self._key(uidl))
        if path is None:
            raise KeyError(uidl)
        return path.read_bytes()

    def _file_path(self, key: str) -> Path | None:
        """Resolve a maildir key to new/ or cur/.

        :param key: Maildir filename. Example: ``"1234567890.M123P1"``
        :return: Path or None. Example: ``Path("var/maildir/new/1234567890.M123P1")``
        """
        for subdir in ("new", "cur"):
            path = self._root / subdir / key
            if path.is_file():
                return path
        return None

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
        pairs: list[tuple[str, int]] = []
        for uidl, key in self._load_uidls().items():
            path = self._file_path(key)
            if path is None:
                continue
            pairs.append((uidl, path.stat().st_size))
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
        raw = path.read_text().strip()
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("MaildirStore._load_uidls | branch | reason=invalid_json")
            return {}
        return {str(key): str(value) for key, value in payload.items()}

    def _save_uidls(self, mapping: dict[str, str]) -> None:
        """Persist uidl map.

        :param mapping: uidl → key. Example: ``{"uid-outlook-1": "1234.M1"}``
        :return: None
        """
        path = self._root / _UIDL_MAP
        tmp = path.with_name("uidl.json.tmp")
        tmp.write_text(json.dumps(mapping))
        tmp.replace(path)
