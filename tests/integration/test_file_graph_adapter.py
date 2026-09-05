"""SYNC — FileGraphAdapter reads fixture files."""

from __future__ import annotations

import pytest

from o365pop.graph.file_adapter import FileGraphAdapter
from tests.support.fixtures import load_graph_case


@pytest.mark.integration
def test_file_graph_adapter_loads_inbox_case() -> None:
    """list_inbox_messages returns AAMk-outlook-1 from fixture JSON.

    :return: None
    """
    adapter = FileGraphAdapter(load_graph_case("SYNC1.1-outlook-q3-close"))
    inbox = adapter.list_inbox_messages()
    assert inbox[0]["id"] == "AAMk-outlook-1"
    mime = adapter.get_message_mime("AAMk-outlook-1")
    assert b"Q3 close" in mime
