"""AUTH1.3 — revoked refresh fails sync_mailbox without retry."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_sync_mailbox_with_revoked_refresh_marks_failed_and_does_not_retry(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Eager Celery: session failed, task not re-enqueued, log reason=auth_failed.

    :param caplog: pytest log capture. Example: test ``caplog``
    :return: None
    """
    raise NotImplementedError()
