"""Mac taskd pull loop. Missing LibreELEC path is TASK1.8 — never raise."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from deploy.entourage.snapshot import Snapshot, SnapshotError, parse_snapshot

logger = logging.getLogger(__name__)


def pull_snapshot(path: Path) -> Snapshot | None:
    """Read and parse ``snapshot.json``. Unreachable path returns None.

    :param path: Snapshot file. Example: ``Path("/storage/o365pop/tasks/snapshot.json")``
    :return: Snapshot or None. Example: ``Snapshot(generated_at="2026-09-11T16:00:00Z", ...)``
    """
    logger.info("taskd.pull | entry | path=%s", path)
    if not path.is_file():
        logger.warning("taskd.pull | branch | reachability=down reason=missing path=%s", path)
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        snapshot = parse_snapshot(payload)
    except (OSError, json.JSONDecodeError, SnapshotError, TypeError) as exc:
        logger.warning(
            "taskd.pull | branch | reachability=down reason=unreadable err=%s",
            type(exc).__name__,
        )
        return None
    logger.info("taskd.pull | exit | lists=%s tasks=%s", len(snapshot.lists), len(snapshot.tasks))
    return snapshot
