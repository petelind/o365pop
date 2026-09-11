"""``python -m deploy.entourage`` — live Mac taskd tick (stdlib + osascript)."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from deploy.entourage.apply import backfill_projects
from deploy.entourage.osascript_entourage import OsascriptEntourage
from deploy.entourage.taskd import pull_snapshot, run_calendar_once, run_once
from deploy.entourage.uid_map import UidMap

logger = logging.getLogger("taskd")


def main(argv: list[str] | None = None) -> int:
    """One 60s tick. Missing snapshot returns 0 (TASK1.8).

    :param argv: Unused CLI args. Example: ``[]``
    :return: Exit code. Example: ``0``
    """
    del argv
    _configure_logging()
    state_dir = Path(os.environ.get("TASK_STATE_DIR") or _default_state_dir())
    task_raw = os.environ.get("TASK_SNAPSHOT_PATH", "").strip()
    cal_raw = os.environ.get("CAL_SNAPSHOT_PATH", "").strip()
    if not task_raw and not cal_raw:
        logger.warning("taskd.pull | branch | reachability=down reason=missing_env")
        return 0
    try:
        if task_raw:
            if os.environ.get("TASK_BACKFILL_PROJECTS", "").strip() == "1":
                result = _backfill_once(Path(task_raw), state_dir)
            else:
                result = run_once(Path(task_raw), state_dir, OsascriptEntourage())
            logger.info(
                "taskd.main | exit | hop=tasks status=%s created=%s", result.get("status"), result.get("created")
            )
        if cal_raw:
            cal_result = run_calendar_once(Path(cal_raw), state_dir, OsascriptEntourage())
            logger.info(
                "taskd.main | exit | hop=calendar status=%s created=%s",
                cal_result.get("status"),
                cal_result.get("created"),
            )
    except Exception as exc:
        logger.warning("taskd.pull | branch | reachability=down reason=%s", type(exc).__name__)
    return 0


def _backfill_once(snapshot_path: Path, state_dir: Path) -> dict[str, object]:
    """Assign Projects on tasks created before project list was wired.

    :param snapshot_path: snapshot.json. Example: ``Path("~/Library/Application Support/o365pop/tasks/snapshot.json")``
    :param state_dir: uid_map parent. Example: ``Path("/Users/denis/Library/Application Support/o365pop")``
    :return: Status. Example: ``{"status": "ok", "created": 0, "updated": 12}``
    """
    snapshot = pull_snapshot(snapshot_path)
    if snapshot is None:
        return {"status": "unreachable", "created": 0, "updated": 0}
    uid_map = UidMap.load(state_dir / "uid_map.json")
    assigned = backfill_projects(snapshot, OsascriptEntourage(), uid_map)
    return {"status": "ok", "created": 0, "updated": assigned}


def _configure_logging() -> None:
    """Log to TASK_LOG_PATH or stderr.

    :return: None
    """
    log_path = Path(os.environ.get("TASK_LOG_PATH") or "")
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        handlers=handlers,
        force=True,
    )


def _default_state_dir() -> Path:
    """Mac uid_map parent.

    :return: Path. Example: ``Path("/Users/denis/Library/Application Support/o365pop")``
    """
    return Path.home() / "Library" / "Application Support" / "o365pop"


if __name__ == "__main__":
    raise SystemExit(main())
