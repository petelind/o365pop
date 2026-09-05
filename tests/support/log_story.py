"""Assert log-story beats against pytest ``caplog`` (TFK-02 helper)."""

from __future__ import annotations

import logging
from typing import Any

LEVEL_NAMES = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


def assert_log_story(
    caplog: Any,
    script: list[dict[str, Any]] | None = None,
    *,
    where: str | None = None,
    beats: dict[str, list[str]] | None = None,
    level: str = "INFO",
) -> None:
    """Fail naming the missing beat or fragment; do not swallow AssertionError.

    Keyword form (TFK-02)::

        assert_log_story(caplog, where="HealthCheck.run",
                         beats={"entry": ["probe=bootstrap"], "exit": ["status=ok"]})

    List form (BOOT) remains supported::

        assert_log_story(caplog, [{"where": "...", "beat": "exit", "must_include": [...]}])

    :param caplog: pytest ``caplog`` fixture. Example: test ``caplog`` argument
    :param script: Optional ordered rows. Example: ``[{"where": "o365pop.cli", "beat": "exit"}]``
    :param where: Logger or Class.method. Example: ``"HealthCheck.run"``
    :param beats: Beat → required fragments. Example: ``{"exit": ["status=ok"]}``
    :param level: Expected level for keyword form. Example: ``"INFO"``
    :return: None
    :raises AssertionError: if a row is missing or out of order
    """
    rows = _normalize_script(script, where=where, beats=beats, level=level)
    search_from = 0
    records = list(caplog.records)
    for index, row in enumerate(rows):
        row_where = str(row["where"])
        beat = str(row["beat"])
        fragments = [str(item) for item in row.get("must_include", [])]
        level_name = str(row.get("level", "INFO")).upper()
        match_at = _find_row(records, search_from, row_where, beat, fragments, level_name)
        if match_at is None:
            rendered = _render_records(records[search_from:])
            raise AssertionError(
                f"log story row {index} not found (where={row_where!r} beat={beat!r} "
                f"must_include={fragments!r} level={level_name}):\n{rendered}"
            )
        search_from = match_at + 1


def _normalize_script(
    script: list[dict[str, Any]] | None,
    *,
    where: str | None,
    beats: dict[str, list[str]] | None,
    level: str,
) -> list[dict[str, Any]]:
    """Build an ordered script from keyword or list form.

    :param script: List-form rows or None. Example: ``None``
    :param where: Shared where for keyword form. Example: ``"HealthCheck.run"``
    :param beats: Keyword-form beats. Example: ``{"exit": ["status=ok"]}``
    :param level: Keyword-form level. Example: ``"INFO"``
    :return: Ordered rows. Example: ``[{"where": "HealthCheck.run", "beat": "exit"}]``
    :raises AssertionError: if neither form is provided
    """
    if beats is not None:
        if not where:
            raise AssertionError("where is required when beats is set")
        return [
            {"where": where, "beat": beat, "must_include": list(fragments), "level": level}
            for beat, fragments in beats.items()
        ]
    if not script:
        raise AssertionError("log story script must not be empty")
    return script


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
        if beat not in record.getMessage():
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
