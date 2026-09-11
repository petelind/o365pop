"""Mac taskd pull loop. Missing LibreELEC path is TASK1.8 — never raise."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from deploy.entourage.apply import apply_snapshot
from deploy.entourage.calendar_apply import apply_calendar_snapshot, apply_pending_acks
from deploy.entourage.calendar_receipts import queue_calendar_receipts
from deploy.entourage.calendar_snapshot import CalendarSnapshot, CalendarSnapshotError, parse_calendar_snapshot
from deploy.entourage.port import EntouragePort
from deploy.entourage.receipts import queue_receipts
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


def pull_calendar_snapshot(path: Path) -> CalendarSnapshot | None:
    """Read and parse ``calendar/snapshot.json``. Unreachable path returns None.

    :param path: Snapshot file. Example: ``Path("/storage/o365pop/calendar/snapshot.json")``
    :return: CalendarSnapshot or None. Example: ``CalendarSnapshot(generated_at="2026-09-11T16:00:00Z", ...)``
    """
    logger.info("taskd.pull | entry | path=%s kind=calendar", path)
    if not path.is_file():
        logger.warning("taskd.pull | branch | reachability=down reason=missing path=%s kind=calendar", path)
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        snapshot = parse_calendar_snapshot(payload)
    except (OSError, json.JSONDecodeError, CalendarSnapshotError, TypeError) as exc:
        logger.warning(
            "taskd.pull | branch | reachability=down reason=unreadable err=%s kind=calendar",
            type(exc).__name__,
        )
        return None
    logger.info(
        "taskd.pull | exit | calendars=%s events=%s kind=calendar",
        len(snapshot.calendars),
        len(snapshot.events),
    )
    return snapshot


def run_calendar_once(snapshot_path: Path, state_dir: Path, entourage: EntouragePort) -> dict[str, object]:
    """Pull calendar snapshot, apply events, queue receipts. Unreachable is CAL1.8 no-op.

    :param snapshot_path: calendar snapshot.json. Example: ``Path("/storage/o365pop/calendar/snapshot.json")``
    :param state_dir: uid_map parent. Example: ``Path("/Users/denis/Library/o365pop")``
    :param entourage: EntouragePort. Example: ``FakeEntourage()``
    :return: Status dict. Example: ``{"status": "ok", "created": 1, "updated": 0}``
    """
    snapshot = pull_calendar_snapshot(snapshot_path)
    if snapshot is None:
        return {"status": "unreachable", "created": 0, "updated": 0}
    cal_root = snapshot_path.parent
    uid_map = UidMap.load(state_dir / "uid_map.json")
    try:
        apply_pending_acks(cal_root / "acks", entourage, uid_map)
        counts = apply_calendar_snapshot(
            snapshot,
            entourage,
            uid_map,
            attachments_root=cal_root / "attachments",
        )
        queued = queue_calendar_receipts(entourage, uid_map, snapshot, cal_root / "receipts")
        return {"status": "ok", "receipts": queued, **counts}
    finally:
        uid_map.save(state_dir / "uid_map.json")


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
    try:
        counts = apply_snapshot(snapshot, entourage, uid_map)
        queued = queue_receipts(entourage, uid_map, snapshot, snapshot_path.parent / "receipts")
        return {"status": "ok", "receipts": queued, **counts}
    finally:
        uid_map.save(state_dir / "uid_map.json")
