"""Persist Graph id → Entourage id joins next to Mac taskd (no SQLite)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class UidMap:
    """Join tables stored as one JSON file (tasks + calendar)."""

    def __init__(self) -> None:
        self.tasks: dict[str, str] = {}
        self.lists: dict[str, str] = {}
        self.categories: dict[str, str] = {}
        self.calendars: dict[str, str] = {}
        self.events: dict[str, str] = {}

    @classmethod
    def load(cls, path: Path) -> UidMap:
        """Read uid_map.json or return empty joins.

        :param path: Map file. Example: ``Path("uid_map.json")``
        :return: Loaded map. Example: ``UidMap()`` with ``lists={"list-work": "1"}``
        """
        mapping = cls()
        if not path.is_file():
            logger.info("taskd.uid_map.load | branch | missing path=%s", path)
            return mapping
        payload = json.loads(path.read_text(encoding="utf-8"))
        mapping.tasks = {str(key): str(value) for key, value in (payload.get("tasks") or {}).items()}
        mapping.lists = {str(key): str(value) for key, value in (payload.get("lists") or {}).items()}
        mapping.categories = {str(key): str(value) for key, value in (payload.get("categories") or {}).items()}
        mapping.calendars = {str(key): str(value) for key, value in (payload.get("calendars") or {}).items()}
        mapping.events = {str(key): str(value) for key, value in (payload.get("events") or {}).items()}
        logger.info(
            "taskd.uid_map.load | exit | tasks=%s lists=%s categories=%s calendars=%s events=%s",
            len(mapping.tasks),
            len(mapping.lists),
            len(mapping.categories),
            len(mapping.calendars),
            len(mapping.events),
        )
        return mapping

    def save(self, path: Path) -> None:
        """Write joins atomically.

        :param path: Map file. Example: ``Path("uid_map.json")``
        :return: None
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.name}.tmp")
        tmp.write_text(
            json.dumps(
                {
                    "tasks": self.tasks,
                    "lists": self.lists,
                    "categories": self.categories,
                    "calendars": self.calendars,
                    "events": self.events,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        tmp.replace(path)
        logger.info("taskd.uid_map.save | exit | path=%s lists=%s", path, len(self.lists))
