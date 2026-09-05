"""SMTP1.1 — AUTH LOGIN + DATA → spool; Graph unused."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_smtp_auth_login_data_writes_spool_without_graph() -> None:
    """Subject Hello Ada in spool/new.

    :return: None
    """
    raise NotImplementedError()
