"""POP1.3 — DELE local only."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_pop_dele_removes_maildir_keeps_tossed_message() -> None:
    """TossedMessage remains; Graph unused.

    :return: None
    """
    raise NotImplementedError()
