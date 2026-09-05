"""Assert log-story script rows against pytest ``caplog`` (TFK-02 helper)."""

from __future__ import annotations

import logging
from typing import Any

LEVEL_NAMES = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


def assert_log_story(caplog: Any, script: list[dict[str, Any]]) -> None:
    """Assert each script row appears in captured logs, in order.

    Each row uses ``where`` (logger name or Class.method), ``beat``,
    ``must_include`` fragments, and optional ``level`` (default INFO).

    :param caplog: pytest ``caplog`` fixture. Example: test ``caplog`` argument
    :param script: Ordered rows. Example: ``[{"where": "o365pop.cli", "beat": "exit", "must_include": ["status=ok"]}]``
    :return: None
    :raises AssertionError: if a row is missing or out of order
    """
    if not script:
        raise AssertionError("log story script must not be empty")
    search_from = 0
    records = list(caplog.records)
    for index, row in enumerate(script):
        where = str(row["where"])
        beat = str(row["beat"])
        fragments = [str(item) for item in row.get("must_include", [])]
        level_name = str(row.get("level", "INFO")).upper()
        match_at = _find_row(records, search_from, where, beat, fragments, level_name)
        if match_at is None:
            rendered = _render_records(records[search_from:])
            raise AssertionError(
                f"log story row {index} not found (where={where!r} beat={beat!r} "
                f"must_include={fragments!r} level={level_name}):\n{rendered}"
            )
        search_from = match_at + 1


def _find_row(
    records: list[logging.LogRecord],
    start: int,
    where: str,
    beat: str,
    fragments: list[str],
    level_name: str,
) -> int | None:
    """Return the index of the next matching record, or None.

    :param records: Captured log records. Example: ``list(caplog.records)``
    :param start: Search start index. Example: ``0``
    :param where: Logger or Class.method. Example: ``"o365pop.cli"``
    :param beat: Required beat token. Example: ``"exit"``
    :param fragments: Extra required strings. Example: ``["status=ok"]``
    :param level_name: Level name. Example: ``"INFO"``
    :return: Matching index or None. Example: ``3``
    """
    expected_level = LEVEL_NAMES.get(level_name)
    for offset, record in enumerate(records[start:]):
        text = f"{record.name} | {record.getMessage()}"
        if expected_level is not None and record.levelno != expected_level:
            continue
        if where not in text:
            continue
        if f"| {beat} |" not in f"| {record.getMessage()} |" and beat not in record.getMessage():
            continue
        if not all(fragment in text for fragment in fragments):
            continue
        return start + offset
    return None


def _render_records(records: list[logging.LogRecord]) -> str:
    """Pretty-print remaining records for assertion failures.

    :param records: Unmatched tail. Example: ``caplog.records[2:]``
    :return: Multiline dump. Example: ``"INFO o365pop.cli | ..."``
    """
    if not records:
        return "  (no further log records)"
    lines = [f"  {record.levelname} {record.name} | {record.getMessage()}" for record in records]
    return "\n".join(lines)
