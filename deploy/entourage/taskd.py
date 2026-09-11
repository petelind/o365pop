"""Mac taskd pull loop. Missing LibreELEC path is TASK1.8 — never raise."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from deploy.entourage.apply import apply_snapshot
from deploy.entourage.port import EntouragePort
from deploy.entourage.snapshot import Snapshot, SnapshotError, parse_snapshot
from deploy.entourage.uid_map import UidMap

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


def run_once(snapshot_path: Path, state_dir: Path, entourage: EntouragePort) -> dict[str, object]:
    """Pull, apply, persist uid_map. Unreachable LibreELEC is a no-op.

    :param snapshot_path: snapshot.json. Example: ``Path("/storage/o365pop/tasks/snapshot.json")``
    :param state_dir: uid_map parent. Example: ``Path("/Users/denis/Library/o365pop")``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :return: Status dict. Example: ``{"status": "ok", "created": 1, "updated": 0}``
    """
    snapshot = pull_snapshot(snapshot_path)
    if snapshot is None:
        return {"status": "unreachable", "created": 0, "updated": 0}
    uid_map = UidMap.load(state_dir / "uid_map.json")
    counts = apply_snapshot(snapshot, entourage, uid_map)
    uid_map.save(state_dir / "uid_map.json")
    return {"status": "ok", **counts}
