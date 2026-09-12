"""TASK1.5 — Graph preset → Entourage color; unknown falls back to gray."""

from __future__ import annotations

import pytest

from deploy.entourage.apply import apply_snapshot
from deploy.entourage.color_map import ENTOURAGE_RGB, entourage_color_rgb, graph_color_to_entourage
from deploy.entourage.snapshot import parse_snapshot
from deploy.entourage.uid_map import UidMap
from tests.support.fake_entourage import FakeEntourage


@pytest.mark.unit
def test_preset1_maps_to_orange() -> None:
    """Locked starter table: preset1 is orange.

    :return: None
    """
    color, fallback = graph_color_to_entourage("preset1")
    assert color == "orange"
    assert fallback is False


@pytest.mark.unit
def test_unknown_preset_falls_back_to_gray() -> None:
    """Unknown Graph color → gray and color_fallback.

    :return: None
    """
    color, fallback = graph_color_to_entourage("preset99")
    assert color == "gray"
    assert fallback is True


@pytest.mark.unit
def test_orange_name_has_sampled_rgb() -> None:
    """Live Entourage sets color as RGB, not an AppleScript enum.

    :return: None
    """
    assert entourage_color_rgb("orange") == ENTOURAGE_RGB["orange"]
    assert entourage_color_rgb("unknown-hue") == ENTOURAGE_RGB["gray"]


@pytest.mark.unit
def test_apply_creates_urgent_with_mapped_preset1_color() -> None:
    """TASK1.5 Urgent/preset1 becomes an Entourage category colored orange.

    :return: None
    """
    entourage = FakeEntourage()
    builtins = {row["name"] for row in entourage.list_categories()}
    uid_map = UidMap()
    snapshot = parse_snapshot(
        {
            "categories": [{"id": "cat-red", "displayName": "Urgent", "color": "preset1"}],
            "lists": [],
            "tasks": [],
        }
    )
    apply_snapshot(snapshot, entourage, uid_map)
    created = [row for row in entourage.list_categories() if row["name"] == "Urgent"]
    assert len(created) == 1
    assert created[0]["color"] == "orange"
    assert created[0]["builtin"] is False
    assert uid_map.categories["cat-red"] == created[0]["id"]
    assert builtins <= {row["name"] for row in entourage.list_categories()}
