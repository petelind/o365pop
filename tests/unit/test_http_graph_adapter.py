"""SYNC — HttpGraphAdapter URL construction (unit; MockTransport allowed)."""

from __future__ import annotations

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
