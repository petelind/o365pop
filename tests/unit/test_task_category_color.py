"""TASK1.5 — Graph preset → Entourage color; unknown falls back to gray."""

from __future__ import annotations

import pytest

from deploy.entourage.color_map import graph_color_to_entourage


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
