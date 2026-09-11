"""Live Entourage 2008 port via osascript. Not imported by ``make test``."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 30


class OsascriptEntourage:
    """Apple Event Entourage surface. Never talks to Graph."""

    def list_tasks(self) -> list[dict[str, Any]]:
        """Return Entourage tasks.

        :return: Task dicts. Example: ``[{"id": "123", "name": "File the Q3 report"}]``
        """
        raw = _osascript(_list_script("tasks", "id,name,completed,content"))
        return [_parse_task_line(line) for line in _lines(raw)]

    def list_projects(self) -> list[dict[str, Any]]:
        """Return Entourage projects.

        :return: Project dicts. Example: ``[{"id": "10", "name": "Work"}]``
        """
        raw = _osascript(_list_script("projects", "id,name"))
        return [_parse_named_line(line) for line in _lines(raw)]

    def list_categories(self) -> list[dict[str, Any]]:
        """Return Entourage categories.

        :return: Category dicts. Example: ``[{"id": "1", "name": "Work"}]``
        """
        raw = _osascript(_list_script("categories", "id,name"))
        return [_parse_named_line(line) for line in _lines(raw)]

    def create_task(self, properties: dict[str, Any]) -> dict[str, Any]:
        """Create a task.

        :param properties: Fields. Example: ``{"name": "File the Q3 report"}``
        :return: Created record. Example: ``{"id": "123", "name": "File the Q3 report"}``
        """
        name = _escape(str(properties.get("name") or ""))
        content = _escape(str(properties.get("content") or ""))
        due = _as_date_literal(properties.get("due"))
        script = (
            'tell application "Microsoft Entourage"\n'
            f'  make new task with properties {{name:"{name}", content:"{content}"{due}}}\n'
            "end tell\n"
        )
        raw = _osascript(script)
        logger.info("OsascriptEntourage.create_task | exit | name_len=%s", len(name))
        return {"id": raw.strip() or "unknown", "name": properties.get("name"), **properties}

    def update_task(self, task_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Set properties on an existing task.

        :param task_id: Entourage id. Example: ``"123"``
        :param properties: Fields. Example: ``{"completed": True}``
        :return: Updated record. Example: ``{"id": "123", "completed": True}``
        """
        assigns = _task_assigns(properties)
        script = f'tell application "Microsoft Entourage"\n  set t to task id {int(task_id)}\n  {assigns}\nend tell\n'
        _osascript(script)
        logger.info("OsascriptEntourage.update_task | exit | id=%s", task_id)
        return {"id": task_id, **properties}

    def delete_task(self, task_id: str) -> None:
        """Delete a task.

        :param task_id: Entourage id. Example: ``"123"``
        :return: None
        """
        _osascript(f'tell application "Microsoft Entourage"\n  delete task id {int(task_id)}\nend tell\n')
        logger.info("OsascriptEntourage.delete_task | exit | id=%s", task_id)

    def create_project(self, name: str) -> dict[str, Any]:
        """Create a project.

        :param name: Project name. Example: ``"Garden"``
        :return: Created record. Example: ``{"id": "10", "name": "Garden"}``
        """
        raw = _osascript(
            'tell application "Microsoft Entourage"\n'
            f'  make new project with properties {{name:"{_escape(name)}"}}\n'
            "end tell\n"
        )
        logger.info("OsascriptEntourage.create_project | exit | name=%s", name)
        return {"id": raw.strip() or "unknown", "name": name}

    def rename_project(self, project_id: str, name: str) -> dict[str, Any]:
        """Rename a project.

        :param project_id: Entourage id. Example: ``"10"``
        :param name: New name. Example: ``"Yard"``
        :return: Updated record. Example: ``{"id": "10", "name": "Yard"}``
        """
        _osascript(
            'tell application "Microsoft Entourage"\n'
            f'  set name of project id {int(project_id)} to "{_escape(name)}"\n'
            "end tell\n"
        )
        return {"id": project_id, "name": name}

    def delete_project(self, project_id: str) -> None:
        """Delete a project.

        :param project_id: Entourage id. Example: ``"10"``
        :return: None
        """
        _osascript(f'tell application "Microsoft Entourage"\n  delete project id {int(project_id)}\nend tell\n')

    def create_category(self, name: str, color: str) -> dict[str, Any]:
        """Create a category.

        :param name: Category name. Example: ``"Urgent"``
        :param color: Entourage color name. Example: ``"orange"``
        :return: Created record. Example: ``{"id": "20", "name": "Urgent", "color": "orange"}``
        """
        raw = _osascript(
            'tell application "Microsoft Entourage"\n'
            f'  make new category with properties {{name:"{_escape(name)}", category color:{color}}}\n'
            "end tell\n"
        )
        logger.info("OsascriptEntourage.create_category | exit | name=%s color=%s", name, color)
        return {"id": raw.strip() or "unknown", "name": name, "color": color, "builtin": False}

    def rename_category(self, category_id: str, name: str) -> dict[str, Any]:
        """Rename a category.

        :param category_id: Entourage id. Example: ``"20"``
        :param name: New name. Example: ``"Critical"``
        :return: Updated record. Example: ``{"id": "20", "name": "Critical"}``
        """
        _osascript(
            'tell application "Microsoft Entourage"\n'
            f'  set name of category id {int(category_id)} to "{_escape(name)}"\n'
            "end tell\n"
        )
        return {"id": category_id, "name": name}

    def set_category_color(self, category_id: str, color: str) -> dict[str, Any]:
        """Set category color.

        :param category_id: Entourage id. Example: ``"20"``
        :param color: Entourage color name. Example: ``"orange"``
        :return: Updated record. Example: ``{"id": "20", "color": "orange"}``
        """
        _osascript(
            'tell application "Microsoft Entourage"\n'
            f"  set category color of category id {int(category_id)} to {color}\n"
            "end tell\n"
        )
        return {"id": category_id, "color": color}


def _osascript(script: str) -> str:
    """Run one AppleScript. Never logs the script body (may contain task titles).

    :param script: AppleScript source. Example: ``'tell application "Microsoft Entourage"\\n...'``
    :return: stdout. Example: ``"123"``
    :raises RuntimeError: if osascript exits non-zero
    """
    logger.info("OsascriptEntourage._osascript | entry | bytes=%s", len(script.encode("utf-8")))
    completed = subprocess.run(
        ["osascript"],
        input=script,
        text=True,
        capture_output=True,
        timeout=_TIMEOUT_SECONDS,
        check=False,
    )
    if completed.returncode != 0:
        logger.error("OsascriptEntourage._osascript | error | rc=%s", completed.returncode)
        raise RuntimeError(f"osascript rc={completed.returncode}")
    return completed.stdout


def _list_script(collection: str, fields: str) -> str:
    """Build a tab-separated dump of a collection.

    :param collection: Entourage collection. Example: ``"tasks"``
    :param fields: Comma field names. Example: ``"id,name"``
    :return: AppleScript. Example: ``tell application ...``
    """
    getters = " & tab & ".join(f"({part.strip()} of aRec as string)" for part in fields.split(","))
    return (
        'tell application "Microsoft Entourage"\n'
        '  set out to ""\n'
        f"  repeat with aRec in {collection}\n"
        f"    set out to out & {getters} & return\n"
        "  end repeat\n"
        "  return out\n"
        "end tell\n"
    )


def _lines(raw: str) -> list[str]:
    """Split osascript stdout.

    :param raw: stdout. Example: ``"1\\tWork\\n"``
    :return: Non-empty lines. Example: ``["1\\tWork"]``
    """
    return [line for line in raw.splitlines() if line.strip()]


def _parse_named_line(line: str) -> dict[str, Any]:
    """Parse id\\tname.

    :param line: One row. Example: ``"10\\tWork"``
    :return: Record. Example: ``{"id": "10", "name": "Work"}``
    """
    parts = line.split("\t")
    return {"id": parts[0].strip(), "name": parts[1].strip() if len(parts) > 1 else ""}


def _parse_task_line(line: str) -> dict[str, Any]:
    """Parse id\\tname\\tcompleted\\tcontent.

    :param line: One row. Example: ``"1\\tFile the Q3 report\\tfalse\\to365pop-uid: task-q3"``
    :return: Record. Example: ``{"id": "1", "completed": False}``
    """
    parts = line.split("\t")
    completed = parts[2].strip().lower() in {"true", "yes"} if len(parts) > 2 else False
    return {
        "id": parts[0].strip(),
        "name": parts[1].strip() if len(parts) > 1 else "",
        "completed": completed,
        "content": parts[3] if len(parts) > 3 else "",
        "categories": [],
        "project_id": None,
        "due": None,
    }


def _escape(value: str) -> str:
    """Escape a string for AppleScript quotes.

    :param value: Raw text. Example: ``'Say "hi"'``
    :return: Escaped. Example: ``'Say \\"hi\\"'``
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _as_date_literal(value: Any) -> str:
    """Optional due date property fragment.

    :param value: datetime or None. Example: ``datetime(2026, 9, 12, 21, 0)``
    :return: Property suffix. Example: ``', due date:date "..."'``
    """
    if not isinstance(value, datetime):
        return ""
    stamp = value.strftime("%A, %B %d, %Y %I:%M:%S %p")
    return f', due date:date "{stamp}"'


def _task_assigns(properties: dict[str, Any]) -> str:
    """AppleScript setters for an update.

    :param properties: Fields. Example: ``{"completed": True}``
    :return: Statements. Example: ``"set completed of t to true"``
    """
    lines: list[str] = []
    if "name" in properties:
        lines.append(f'set name of t to "{_escape(str(properties["name"]))}"')
    if "content" in properties:
        lines.append(f'set content of t to "{_escape(str(properties["content"]))}"')
    if "completed" in properties:
        lines.append(f"set completed of t to {str(bool(properties['completed'])).lower()}")
    if isinstance(properties.get("due"), datetime):
        stamp = properties["due"].strftime("%A, %B %d, %Y %I:%M:%S %p")
        lines.append(f'set due date of t to date "{stamp}"')
    return "\n  ".join(lines) if lines else "return"
