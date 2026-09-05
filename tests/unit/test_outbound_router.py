"""TEAM1.1–1.4 decision table."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_route_in_reply_to_teams_message_id_is_teams_chat() -> None:
    """In-Reply-To matching TossedMessage → teams_chat.

    :return: None
    """
    raise NotImplementedError()


@pytest.mark.unit
def test_route_unknown_o365pop_local_is_map_miss() -> None:
    """teams.unknown@o365pop.local → map_miss.

    :return: None
    """
    raise NotImplementedError()
