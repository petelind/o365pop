"""SYNC — FileGraphAdapter reads fixture files."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_file_graph_adapter_loads_inbox_case() -> None:
    """list_inbox_messages returns AAMk-outlook-1 from fixture JSON.

    :return: None
    """
    raise NotImplementedError()
