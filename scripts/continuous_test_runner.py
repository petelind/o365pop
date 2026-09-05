"""Poll ``o365pop/`` and ``tests/`` and re-run pytest (TFK-02 / do-continuous-testing)."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

POLL_SECONDS = 2.0
WATCH_ROOTS = ("o365pop", "tests")


def _mtime_stamp(roots: tuple[str, ...]) -> float:
    """Newest ``.py`` mtime under the watched roots.

    :param roots: Relative directories. Example: ``("o365pop", "tests")``
    :return: Latest mtime or ``0.0``. Example: ``1710000000.0``
    """
    newest = 0.0
    for root in roots:
        base = Path(root)
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            newest = max(newest, path.stat().st_mtime)
    return newest


def _run_pytest() -> int:
    """Run the merge-gate pytest command.

    :return: pytest exit code. Example: ``0``
    """
    command = [sys.executable, "-m", "pytest", "tests/", "-m", "not live_graph", "-q"]
    print("continuous_test_runner | processing | cmd=", " ".join(command), flush=True)
    return subprocess.call(command)


def main() -> int:
    """Watch for changes until interrupted.

    :return: Last pytest exit code. Example: ``0``
    """
    print("continuous_test_runner | entry | watching=", WATCH_ROOTS, flush=True)
    last = _mtime_stamp(WATCH_ROOTS)
    code = _run_pytest()
    try:
        while True:
            time.sleep(POLL_SECONDS)
            current = _mtime_stamp(WATCH_ROOTS)
            if current > last:
                last = current
                print("continuous_test_runner | branch | change detected", flush=True)
                code = _run_pytest()
    except KeyboardInterrupt:
        print("continuous_test_runner | exit | status=stopped", flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
