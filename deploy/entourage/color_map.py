"""Graph ``outlookCategory.color`` → Entourage category color name."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

GRAPH_TO_ENTOURAGE: dict[str, str] = {
    "none": "gray",
    "preset0": "red",
    "preset1": "orange",
    "preset2": "maroon",
    "preset3": "yellow",
    "preset4": "green",
    "preset5": "steel",
    "preset6": "olive",
    "preset7": "blue",
    "preset8": "purple",
    "preset9": "cranberry",
    "preset10": "steel",
    "preset11": "maroon",
    "preset12": "gray",
    "preset13": "gray",
    "preset14": "gray",
    "preset15": "red",
    "preset16": "orange",
    "preset17": "maroon",
    "preset18": "yellow",
    "preset19": "green",
    "preset20": "steel",
    "preset21": "olive",
    "preset22": "blue",
    "preset23": "purple",
    "preset24": "cranberry",
}
FALLBACK_COLOR = "gray"


def graph_color_to_entourage(color: str) -> tuple[str, bool]:
    """Map a Graph preset to an Entourage color name.

    :param color: Graph color token. Example: ``"preset1"``
    :return: ``(entourage_name, fallback)``. Example: ``("orange", False)``
    """
    key = (color or "").strip().lower()
    mapped = GRAPH_TO_ENTOURAGE.get(key)
    if mapped is not None:
        logger.info("taskd.color_map | exit | graph=%s entourage=%s color_fallback=false", key, mapped)
        return mapped, False
    logger.info(
        "taskd.color_map | branch | graph=%s entourage=%s color_fallback=true",
        key or "empty",
        FALLBACK_COLOR,
    )
    return FALLBACK_COLOR, True
