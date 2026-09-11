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
