"""Live Entourage 2008 port via osascript. Not imported by ``make test``."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from typing import Any

from deploy.entourage.color_map import entourage_color_rgb

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
        raw = _osascript(_task_create_script(properties))
        logger.info("OsascriptEntourage.create_task | exit | name_len=%s", len(str(properties.get("name") or "")))
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
            f'  set p to make new project with properties {{name:"{_escape(name)}"}}\n'
            "  return id of p as string\n"
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
        rgb = _rgb_literal(color)
        raw = _osascript(
            'tell application "Microsoft Entourage"\n'
            f'  set c to make new category with properties {{name:"{_escape(name)}"}}\n'
            f"  set color of c to {rgb}\n"
            "  return id of c as string\n"
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
        rgb = _rgb_literal(color)
        _osascript(
            'tell application "Microsoft Entourage"\n'
            f"  set color of category id {int(category_id)} to {rgb}\n"
            "end tell\n"
        )
        return {"id": category_id, "color": color}

    def list_events(self) -> list[dict[str, Any]]:
        """Return Entourage calendar events.

        :return: Event dicts. Example: ``[{"id": "5", "subject": "Standup"}]``
        """
        raw = _osascript(_list_script("events", "id,subject,content"))
        return [_parse_event_line(line) for line in _lines(raw)]

    def create_event(self, properties: dict[str, Any]) -> dict[str, Any]:
        """Create a calendar event.

        :param properties: Fields. Example: ``{"subject": "Standup"}``
        :return: Created record. Example: ``{"id": "5", "subject": "Standup"}``
        """
        raw = _osascript(_event_create_script(properties))
        logger.info(
            "OsascriptEntourage.create_event | exit | subject_len=%s", len(str(properties.get("subject") or ""))
        )
        return {"id": raw.strip() or "unknown", **properties}

    def update_event(self, event_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Set properties on an existing event.

        :param event_id: Entourage id. Example: ``"5"``
        :param properties: Fields. Example: ``{"subject": "Standup moved"}``
        :return: Updated record. Example: ``{"id": "5", "subject": "Standup moved"}``
        """
        assigns = _event_assigns(properties)
        script = f'tell application "Microsoft Entourage"\n  set e to event id {int(event_id)}\n  {assigns}\nend tell\n'
        _osascript(script)
        logger.info("OsascriptEntourage.update_event | exit | id=%s", event_id)
        return {"id": event_id, **properties}

    def delete_event(self, event_id: str) -> None:
        """Delete a calendar event.

        :param event_id: Entourage id. Example: ``"5"``
        :return: None
        """
        _osascript(f'tell application "Microsoft Entourage"\n  delete event id {int(event_id)}\nend tell\n')
        logger.info("OsascriptEntourage.delete_event | exit | id=%s", event_id)

    def get_event_content(self, event_id: str) -> str:
        """Return event notes/content.

        :param event_id: Entourage id. Example: ``"5"``
        :return: Content text. Example: ``"o365pop-uid: evt-standup"``
        """
        raw = _osascript(
            f'tell application "Microsoft Entourage"\n  return content of event id {int(event_id)}\nend tell\n'
        )
        return raw.strip()

    def add_event_attachment(self, event_id: str, name: str, content_type: str, content: bytes) -> dict[str, Any]:
        """Attach a file to an event (live path; not used in CI).

        :param event_id: Entourage id. Example: ``"5"``
        :param name: File name. Example: ``"agenda.pdf"``
        :param content_type: MIME type. Example: ``"application/pdf"``
        :param content: Raw bytes. Example: ``b"%PDF-1.4"``
        :return: Attachment record. Example: ``{"name": "agenda.pdf", "bytes": 32}``
        """
        del content_type
        # TODO: operator live smoke — Entourage 2008 attachment API varies by dictionary version.
        logger.warning(
            "OsascriptEntourage.add_event_attachment | branch | live_attachment=stub event_id=%s name=%s bytes=%s",
            event_id,
            name,
            len(content),
        )
        return {"name": name, "bytes": len(content)}


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
        err = (completed.stderr or "").replace("\n", " ")[:200]
        logger.error("OsascriptEntourage._osascript | error | rc=%s err=%s", completed.returncode, err)
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


def _rgb_literal(color: str) -> str:
    """AppleScript RGB list for an Entourage color name.

    :param color: Color name. Example: ``"orange"``
    :return: Literal. Example: ``"{56026, 38689, 63285}"``
    """
    red, green, blue = entourage_color_rgb(color)
    return f"{{{red}, {green}, {blue}}}"


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
    project_line = _project_assign(properties)
    if project_line:
        lines.append(project_line)
    return "\n  ".join(lines) if lines else "return"


def _task_create_script(properties: dict[str, Any]) -> str:
    """AppleScript to create a task and assign its Project.

    :param properties: Fields. Example: ``{"name": "File the Q3 report", "project_id": "12"}``
    :return: Script. Example: ``tell application "Microsoft Entourage"...``
    """
    name = _escape(str(properties.get("name") or ""))
    content = _escape(str(properties.get("content") or ""))
    due = _as_date_literal(properties.get("due"))
    assign = _project_assign(properties)
    extra = f"  {assign}\n" if assign else ""
    if properties.get("completed") is True:
        extra += "  set completed of t to true\n"
    return (
        'tell application "Microsoft Entourage"\n'
        f'  set t to make new task with properties {{name:"{name}", content:"{content}"{due}}}\n'
        f"{extra}"
        "  return id of t as string\n"
        "end tell\n"
    )


def _parse_event_line(line: str) -> dict[str, Any]:
    """Parse id\\tsubject\\tcontent.

    :param line: One row. Example: ``"5\\tStandup\\to365pop-uid: evt-standup"``
    :return: Record. Example: ``{"id": "5", "subject": "Standup"}``
    """
    parts = line.split("\t")
    return {
        "id": parts[0].strip(),
        "subject": parts[1].strip() if len(parts) > 1 else "",
        "content": parts[2] if len(parts) > 2 else "",
        "categories": [],
        "project_id": None,
        "location": "",
        "reminder_minutes": None,
        "show_as": "busy",
        "sensitivity": "normal",
        "to_recipients": [],
        "start": None,
        "end": None,
    }


def _event_assigns(properties: dict[str, Any]) -> str:
    """AppleScript setters for an event update.

    :param properties: Fields. Example: ``{"subject": "Standup moved"}``
    :return: Statements. Example: ``"set subject of e to \\"Standup moved\\""``
    """
    lines: list[str] = []
    if "subject" in properties:
        lines.append(f'set subject of e to "{_escape(str(properties["subject"]))}"')
    if "content" in properties:
        lines.append(f'set content of e to "{_escape(str(properties["content"]))}"')
    if "location" in properties:
        lines.append(f'set location of e to "{_escape(str(properties["location"]))}"')
    project_line = _project_assign_event(properties)
    if project_line:
        lines.append(project_line)
    return "\n  ".join(lines) if lines else "return"


def _event_create_script(properties: dict[str, Any]) -> str:
    """AppleScript to create an event and assign its Project.

    :param properties: Fields. Example: ``{"subject": "Standup", "project_id": "12"}``
    :return: Script. Example: ``tell application "Microsoft Entourage"...``
    """
    subject = _escape(str(properties.get("subject") or ""))
    content = _escape(str(properties.get("content") or ""))
    location = _escape(str(properties.get("location") or ""))
    assign = _project_assign_event(properties)
    extra = f"  {assign}\n" if assign else ""
    props = f'subject:"{subject}", content:"{content}", location:"{location}"'
    return (
        'tell application "Microsoft Entourage"\n'
        f"  set e to make new event with properties {{{props}}}\n"
        f"{extra}"
        "  return id of e as string\n"
        "end tell\n"
    )


def _project_assign_event(properties: dict[str, Any]) -> str:
    """AppleScript to set event ``project list`` from ``project_id``.

    :param properties: Fields. Example: ``{"project_id": "12"}``
    :return: Statement or empty. Example: ``"set project list of e to {project id 12}"``
    """
    raw = properties.get("project_id")
    if raw in (None, ""):
        return ""
    try:
        project_id = int(raw)
    except (TypeError, ValueError):
        return ""
    return f"set project list of e to {{project id {project_id}}}"


def _project_assign(properties: dict[str, Any]) -> str:
    """AppleScript to set ``project list`` from ``project_id``.

    :param properties: Fields. Example: ``{"project_id": "12"}``
    :return: Statement or empty. Example: ``"set project list of t to {project id 12}"``
    """
    raw = properties.get("project_id")
    if raw in (None, ""):
        return ""
    try:
        project_id = int(raw)
    except (TypeError, ValueError):
        return ""
    return f"set project list of t to {{project id {project_id}}}"
