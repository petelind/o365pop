"""SYNC — eager Celery pull+toss."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_sync_mailbox_eager_tosses_file_graph_case() -> None:
    """Completed session with tossed>=1 on fixture case.

    :return: None
    """
    raise NotImplementedError()
