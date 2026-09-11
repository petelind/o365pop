"""Live Entourage 2008 port via osascript. Not imported by ``make test``."""

from __future__ import annotations

import logging
import subprocess
import time
from datetime import datetime
from typing import Any

from deploy.entourage.color_map import entourage_color_rgb

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 120


class OsascriptEntourage:
    """Apple Event Entourage surface. Never talks to Graph."""

    def list_tasks(self) -> list[dict[str, Any]]:
        """Return Entourage tasks.

        :return: Task dicts. Example: ``[{"id": "123", "name": "File the Q3 report"}]``
        """
        raw = _osascript(_list_script("tasks", "id,name,completed,content"), op="list_tasks")
        return [_parse_task_line(line) for line in _lines(raw)]

    def list_projects(self) -> list[dict[str, Any]]:
        """Return Entourage projects.

        :return: Project dicts. Example: ``[{"id": "10", "name": "Work"}]``
        """
        raw = _osascript(_list_script("projects", "id,name"), op="list_projects")
        return [_parse_named_line(line) for line in _lines(raw)]

    def list_categories(self) -> list[dict[str, Any]]:
        """Return Entourage categories.

        :return: Category dicts. Example: ``[{"id": "1", "name": "Work"}]``
        """
        raw = _osascript(_list_script("categories", "id,name"), op="list_categories")
        return [_parse_named_line(line) for line in _lines(raw)]

    def create_task(self, properties: dict[str, Any]) -> dict[str, Any]:
        """Create a task.

        :param properties: Fields. Example: ``{"name": "File the Q3 report"}``
        :return: Created record. Example: ``{"id": "123", "name": "File the Q3 report"}``
        """
        raw = _osascript(_task_create_script(properties), op="create_task")
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
        _osascript(script, op="update_task")
        logger.info("OsascriptEntourage.update_task | exit | id=%s", task_id)
        return {"id": task_id, **properties}

    def delete_task(self, task_id: str) -> None:
        """Delete a task.

        :param task_id: Entourage id. Example: ``"123"``
        :return: None
        """
        _osascript(
            f'tell application "Microsoft Entourage"\n  delete task id {int(task_id)}\nend tell\n',
            op="delete_task",
        )
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
            "end tell\n",
            op="create_project",
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
            "end tell\n",
            op="rename_project",
        )
        return {"id": project_id, "name": name}

    def delete_project(self, project_id: str) -> None:
        """Delete a project.

        :param project_id: Entourage id. Example: ``"10"``
        :return: None
        """
        _osascript(
            f'tell application "Microsoft Entourage"\n  delete project id {int(project_id)}\nend tell\n',
            op="delete_project",
        )

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
            "end tell\n",
            op="create_category",
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
            "end tell\n",
            op="rename_category",
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
            "end tell\n",
            op="set_category_color",
        )
        return {"id": category_id, "color": color}

    def list_events(self) -> list[dict[str, Any]]:
        """Return Entourage calendar events.

        :return: Event dicts. Example: ``[{"id": "5", "subject": "Standup"}]``
        """
        raw = _osascript(_list_script("events", "id,subject,content"), op="list_events")
        return [_parse_event_line(line) for line in _lines(raw)]

    def create_event(self, properties: dict[str, Any]) -> dict[str, Any]:
        """Create a calendar event.

        :param properties: Fields. Example: ``{"subject": "Standup"}``
        :return: Created record. Example: ``{"id": "5", "subject": "Standup"}``
        """
        raw = _osascript(_event_create_script(properties), op="create_event")
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
        script = (
            'tell application "Microsoft Entourage"\n'
            '  log "event_update get"\n'
            f"  set e to event id {int(event_id)}\n"
            '  log "event_update assign"\n'
            f"  {assigns}\n"
            '  log "event_update done"\n'
            "end tell\n"
        )
        _osascript(script, op="update_event")
        logger.info("OsascriptEntourage.update_event | exit | id=%s", event_id)
        return {"id": event_id, **properties}

    def delete_event(self, event_id: str) -> None:
        """Delete a calendar event.

        :param event_id: Entourage id. Example: ``"5"``
        :return: None
        """
        _osascript(
            f'tell application "Microsoft Entourage"\n  delete event id {int(event_id)}\nend tell\n',
            op="delete_event",
        )
        logger.info("OsascriptEntourage.delete_event | exit | id=%s", event_id)

    def get_event_content(self, event_id: str) -> str:
        """Return event notes/content.

        :param event_id: Entourage id. Example: ``"5"``
        :return: Content text. Example: ``"o365pop-uid: evt-standup"``
        """
        raw = _osascript(
            f'tell application "Microsoft Entourage"\n  return content of event id {int(event_id)}\nend tell\n',
            op="get_event_content",
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


def _osascript(script: str, op: str = "script") -> str:
    """Run one AppleScript. Never logs the script body (may contain titles or HTML).

    :param script: AppleScript source. Example: ``'tell application "Microsoft Entourage"\\n...'``
    :param op: Caller label for log beats. Example: ``"create_event"``
    :return: stdout. Example: ``"123"``
    :raises RuntimeError: if osascript exits non-zero
    :raises subprocess.TimeoutExpired: if the process exceeds ``_TIMEOUT_SECONDS``
    """
    started = time.monotonic()
    nbytes = len(script.encode("utf-8"))
    logger.info("OsascriptEntourage._osascript | entry | op=%s bytes=%s", op, nbytes)
    try:
        completed = subprocess.run(
            ["osascript"],
            input=script,
            text=True,
            capture_output=True,
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.error(
            "OsascriptEntourage._osascript | error | op=%s rc=timeout elapsed_ms=%s bytes=%s",
            op,
            elapsed_ms,
            nbytes,
        )
        raise
    elapsed_ms = int((time.monotonic() - started) * 1000)
    err = (completed.stderr or "").replace("\n", " | ")[:400]
    if completed.returncode != 0:
        logger.error(
            "OsascriptEntourage._osascript | error | op=%s rc=%s elapsed_ms=%s err=%s",
            op,
            completed.returncode,
            elapsed_ms,
            err,
        )
        raise RuntimeError(f"osascript rc={completed.returncode} op={op}")
    logger.info(
        "OsascriptEntourage._osascript | exit | op=%s elapsed_ms=%s stdout_len=%s stderr=%s",
        op,
        elapsed_ms,
        len(completed.stdout or ""),
        err,
    )
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
    """Escape a string for AppleScript double-quoted literals.

    :param value: Raw text. Example: ``'Say "hi"\\nline two'``
    :return: Escaped. Example: ``'Say \\"hi\\"\\nline two'``
    """
    return (
        value.replace("\\", "\\\\").replace('"', '\\"').replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
    )


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


def _applescript_date(value: datetime) -> str:
    """Format an aware datetime for Entourage ``date "..."`` literals (local wall time).

    :param value: UTC or aware instant. Example: ``datetime(2026, 9, 12, 13, 0, tzinfo=timezone.utc)``
    :return: AppleScript date text. Example: ``"Saturday, September 12, 2026 09:00:00 AM"``
    """
    local = value.astimezone()
    return local.strftime("%A, %B %d, %Y %I:%M:%S %p")


def _event_time_props(properties: dict[str, Any]) -> list[str]:
    """Build ``start time`` / ``end time`` property fragments for event AppleScript.

    :param properties: Event fields. Example: ``{"start": datetime(...), "end": datetime(...)}``
    :return: Property fragments. Example: ``['start time:date "Saturday, ... AM"']``
    """
    parts: list[str] = []
    start = properties.get("start")
    end = properties.get("end")
    if isinstance(start, datetime):
        parts.append(f'start time:date "{_applescript_date(start)}"')
    if isinstance(end, datetime):
        parts.append(f'end time:date "{_applescript_date(end)}"')
    if properties.get("all_day") is True:
        parts.append("all day event:true")
    return parts


def _event_content_text(properties: dict[str, Any]) -> tuple[str, str]:
    """Return HTML and plain event notes. Entourage events have no ``plain text content``.

    :param properties: Event fields. Example: ``{"content_html": "<p>Hi</p>", "content_plain": "Hi"}``
    :return: HTML then plain. Example: ``("<p>Hi</p>", "Hi")``
    """
    html = str(properties.get("content_html") or "").strip()
    plain = str(properties.get("content_plain") or properties.get("content") or "").strip()
    return html, plain


def _event_content_prop(properties: dict[str, Any]) -> str:
    """AppleScript property fragment for event body (always ``content``).

    :param properties: Event fields. Example: ``{"content_html": "<p>Hi</p>"}``
    :return: Property fragment. Example: ``'content:"<html>..."'``
    """
    html, plain = _event_content_text(properties)
    text = html or plain
    return f'content:"{_escape(text)}"'


def _event_content_assign(properties: dict[str, Any]) -> str:
    """AppleScript setter for event notes via ``content`` (not ``plain text content``).

    Entourage 2008 events raise -1728 ``Can't get content`` when the script
    uses ``plain text content``. HTML that Entourage rejects falls back to plain.

    :param properties: Event fields. Example: ``{"content_html": "<p>Hi</p>"}``
    :return: Statement or empty. Example: ``'set content of e to "..."'``
    """
    html, plain = _event_content_text(properties)
    if html and plain:
        return (
            "try\n"
            f'    set content of e to "{_escape(html)}"\n'
            "  on error\n"
            f'    set content of e to "{_escape(plain)}"\n'
            "  end try"
        )
    text = html or plain
    if not text:
        return ""
    return f'set content of e to "{_escape(text)}"'


def _event_assigns(properties: dict[str, Any]) -> str:
    """AppleScript setters for an event update.

    :param properties: Fields. Example: ``{"subject": "Standup moved"}``
    :return: Statements. Example: ``"set subject of e to \\"Standup moved\\""``
    """
    lines: list[str] = []
    if "subject" in properties:
        lines.append(f'set subject of e to "{_escape(str(properties["subject"]))}"')
    content_line = _event_content_assign(properties)
    if content_line:
        lines.append(content_line)
    if "location" in properties:
        lines.append(f'set location of e to "{_escape(str(properties["location"]))}"')
    start = properties.get("start")
    end = properties.get("end")
    if isinstance(start, datetime):
        lines.append(f'set start time of e to date "{_applescript_date(start)}"')
    if isinstance(end, datetime):
        lines.append(f'set end time of e to date "{_applescript_date(end)}"')
    if properties.get("all_day") is True:
        lines.append("set all day event of e to true")
    category_line = _category_assign_event(properties)
    if category_line:
        lines.append(category_line)
    project_line = _project_assign_event(properties)
    if project_line:
        lines.append(project_line)
    return "\n  ".join(lines) if lines else "return"


def _event_create_script(properties: dict[str, Any]) -> str:
    """AppleScript to create an event and assign its Project.

    Body fields are set after ``make new event`` via ``content`` — Entourage
    events have no ``plain text content``, and that token cannot appear inside
    a ``with properties`` record (AppleScript -2741).

    :param properties: Fields. Example: ``{"subject": "Standup", "project_id": "12"}``
    :return: Script. Example: ``tell application "Microsoft Entourage"...``
    """
    subject = _escape(str(properties.get("subject") or ""))
    location = _escape(str(properties.get("location") or ""))
    time_props = _event_time_props(properties)
    project_prop = _event_project_prop(properties)
    prop_parts = [f'subject:"{subject}"', f'location:"{location}"']
    if project_prop:
        prop_parts.append(project_prop)
    if time_props:
        prop_parts.extend(time_props)
    props = ", ".join(prop_parts)
    after_create = [
        _event_content_assign(properties),
        _project_assign_event(properties),
        _category_assign_event(properties),
    ]
    extra = "".join(f"  {line}\n" for line in after_create if line)
    return (
        'tell application "Microsoft Entourage"\n'
        '  log "event_create make"\n'
        f"  set e to make new event with properties {{{props}}}\n"
        '  log "event_create content"\n'
        f"{extra}"
        '  log "event_create done"\n'
        "  return id of e as string\n"
        "end tell\n"
    )


def _event_project_id(properties: dict[str, Any]) -> int | None:
    """Parse Entourage project id from event properties.

    :param properties: Event fields. Example: ``{"project_id": "12"}``
    :return: Numeric id or None. Example: ``12``
    """
    raw = properties.get("project_id")
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _event_project_prop(properties: dict[str, Any]) -> str:
    """Build ``project list`` fragment for ``make new event with properties``.

    :param properties: Event fields. Example: ``{"project_id": "12"}``
    :return: Property fragment or empty. Example: ``"project list:{project id 12}"``
    """
    project_id = _event_project_id(properties)
    if project_id is None:
        return ""
    return f"project list:{{project id {project_id}}}"


def _category_assign_event(properties: dict[str, Any]) -> str:
    """AppleScript to set event ``category`` list from category names.

    :param properties: Event fields. Example: ``{"categories": ["Work", "Urgent"]}``
    :return: Statement or empty. Example: ``"set category of e to {category \\"Work\\"}"``
    """
    names = properties.get("categories") or []
    if not isinstance(names, list) or not names:
        return ""
    parts = ", ".join(f'category "{_escape(str(name))}"' for name in names if str(name).strip())
    if not parts:
        return ""
    return f"set category of e to {{{parts}}}"


def _project_assign_event(properties: dict[str, Any]) -> str:
    """AppleScript to set event ``project list`` from ``project_id``.

    :param properties: Fields. Example: ``{"project_id": "12"}``
    :return: Statement or empty. Example: ``"set project list of e to {project id 12}"``
    """
    project_id = _event_project_id(properties)
    if project_id is None:
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
