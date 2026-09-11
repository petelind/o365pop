"""``python -m deploy.entourage`` — live Mac taskd tick (stdlib + osascript)."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from deploy.entourage.osascript_entourage import OsascriptEntourage
from deploy.entourage.taskd import run_once

logger = logging.getLogger("taskd")


def main(argv: list[str] | None = None) -> int:
    """One 60s tick. Missing snapshot returns 0 (TASK1.8).

    :param argv: Unused CLI args. Example: ``[]``
    :return: Exit code. Example: ``0``
    """
    del argv
    _configure_logging()
    raw = os.environ.get("TASK_SNAPSHOT_PATH", "").strip()
    if not raw:
        logger.warning("taskd.pull | branch | reachability=down reason=missing_env")
        return 0
    state_dir = Path(os.environ.get("TASK_STATE_DIR") or _default_state_dir())
    try:
        result = run_once(Path(raw), state_dir, OsascriptEntourage())
        logger.info("taskd.main | exit | status=%s created=%s", result.get("status"), result.get("created"))
    except Exception as exc:
        logger.warning("taskd.pull | branch | reachability=down reason=%s", type(exc).__name__)
    return 0


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
