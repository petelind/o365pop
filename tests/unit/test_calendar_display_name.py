"""Calendar snapshot publisher keeps calendar displayName when Graph sends name only."""

from __future__ import annotations

import pytest

from o365pop.tosser.calendar_snapshot import _public_calendar


@pytest.mark.unit
def test_public_calendar_falls_back_to_name_field() -> None:
    """Graph /me/calendars often exposes name without displayName.

    :return: None
    """
    row = _public_calendar({"id": "cal-work", "name": "Calendar"})
    assert row["displayName"] == "Calendar"
