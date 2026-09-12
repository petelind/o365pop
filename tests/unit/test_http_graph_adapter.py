"""SYNC — HttpGraphAdapter URL construction (unit; MockTransport allowed)."""

from __future__ import annotations

import base64

import httpx
import pytest

from o365pop.graph.http_adapter import GRAPH_ROOT, HttpGraphAdapter


def _client_capturing(handler) -> httpx.Client:
    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport)


@pytest.mark.unit
def test_list_inbox_messages_uses_inbox_messages_path() -> None:
    """GET path is /me/mailFolders/inbox/messages.

    :return: None
    """
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"value": [{"id": "AAMk-1", "subject": "Q3 close"}]})

    adapter = HttpGraphAdapter("eyJ0-test", client=_client_capturing(handler))
    rows = adapter.list_inbox_messages()
    assert rows[0]["id"] == "AAMk-1"
    assert seen[0] == f"{GRAPH_ROOT}/me/mailFolders/inbox/messages"


@pytest.mark.unit
def test_send_mime_posts_base64_text_plain() -> None:
    """Graph sendMail rejects raw MIME; body must be base64 (ErrorMimeContentInvalidBase64String).

    :return: None
    """
    rfc822 = b"Subject: Hello\r\n\r\nHi"
    seen: list[tuple[str, str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.headers.get("content-type", ""), request.content))
        return httpx.Response(202)

    adapter = HttpGraphAdapter("eyJ0-test", client=_client_capturing(handler))
    adapter.send_mime(rfc822)
    content_type, body = seen[0]
    assert content_type.startswith("text/plain")
    assert body == base64.b64encode(rfc822)
    assert rfc822 not in (body,)


@pytest.mark.unit
def test_list_todo_lists_uses_todo_lists_path() -> None:
    """GET path is /me/todo/lists.

    :return: None
    """
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"value": [{"id": "list-work"}]})

    adapter = HttpGraphAdapter("eyJ0-test", client=_client_capturing(handler))
    rows = adapter.list_todo_lists()
    assert rows[0]["id"] == "list-work"
    assert seen[0] == f"{GRAPH_ROOT}/me/todo/lists"


@pytest.mark.unit
def test_patch_todo_task_uses_list_and_task_path() -> None:
    """PATCH path includes list id and task id.

    :return: None
    """
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, str(request.url)))
        return httpx.Response(200, json={"id": "task-q3", "status": "completed"})

    adapter = HttpGraphAdapter("eyJ0-test", client=_client_capturing(handler))
    adapter.patch_todo_task("list-work", "task-q3", {"status": "completed"})
    assert seen[0] == ("PATCH", f"{GRAPH_ROOT}/me/todo/lists/list-work/tasks/task-q3")


@pytest.mark.unit
def test_list_calendar_view_follows_odata_next_link() -> None:
    """calendarView must paginate; Graph defaults to 10 rows per page.

    :return: None
    """
    calls: list[str] = []
    page2 = f"{GRAPH_ROOT}/me/calendars/cal-work/calendarView?$skip=10"

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if len(calls) == 1:
            return httpx.Response(
                200,
                json={
                    "value": [{"id": "evt-1", "subject": "Standup"}],
                    "@odata.nextLink": page2,
                },
            )
        return httpx.Response(200, json={"value": [{"id": "evt-2", "subject": "Review"}]})

    adapter = HttpGraphAdapter("eyJ0-test", client=_client_capturing(handler))
    rows = adapter.list_calendar_view("cal-work", "2026-08-12T00:00:00Z", "2027-03-10T00:00:00Z")
    assert [row["id"] for row in rows] == ["evt-1", "evt-2"]
    assert len(calls) == 2
    assert "$top=100" in calls[0]


@pytest.mark.unit
def test_list_calendar_view_sends_prefer_text_body() -> None:
    """calendarView must ask Graph for text bodies on every page.

    :return: None
    """
    prefers: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        prefers.append(request.headers.get("prefer", ""))
        if len(prefers) == 1:
            return httpx.Response(
                200,
                json={
                    "value": [{"id": "evt-1"}],
                    "@odata.nextLink": f"{GRAPH_ROOT}/me/calendars/cal-work/calendarView?$skip=10",
                },
            )
        return httpx.Response(200, json={"value": [{"id": "evt-2"}]})

    adapter = HttpGraphAdapter("eyJ0-test", client=_client_capturing(handler))
    adapter.list_calendar_view("cal-work", "2026-08-12T00:00:00Z", "2027-03-10T00:00:00Z")
    assert prefers == ['outlook.body-content-type="text"', 'outlook.body-content-type="text"']
