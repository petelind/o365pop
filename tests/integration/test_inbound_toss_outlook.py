"""SYNC1.1 — Outlook MIME toss + dedup."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_toss_outlook_writes_one_maildir_message_and_skips_duplicate() -> None:
    """Subject Q3 close; second toss skipped_dup=1.

    :return: None
    """
    raise NotImplementedError()
