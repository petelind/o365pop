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
# 16-bit RGB sampled from Entourage 2008 built-in categories (Family=red, …).
ENTOURAGE_RGB: dict[str, tuple[int, int, int]] = {
    "red": (52428, 26646, 44325),
    "orange": (56026, 38689, 63285),
    "green": (61166, 34589, 33052),
    "gray": (39970, 39970, 39970),
    "purple": (38036, 49193, 35102),
    "blue": (47802, 50474, 65335),
    "steel": (48059, 32796, 25109),
    "yellow": (65535, 48425, 26390),
    "maroon": (50017, 11847, 30666),
    "olive": (54360, 61876, 27927),
    "cranberry": (50017, 11847, 30666),
}


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


def entourage_color_rgb(name: str) -> tuple[int, int, int]:
    """Return 16-bit RGB for an Entourage color name.

    :param name: Color name. Example: ``"orange"``
    :return: RGB triple. Example: ``(56026, 38689, 63285)``
    """
    key = (name or "").strip().lower()
    rgb = ENTOURAGE_RGB.get(key) or ENTOURAGE_RGB[FALLBACK_COLOR]
    logger.info("taskd.color_map | exit | rgb_name=%s r=%s g=%s b=%s", key or "empty", rgb[0], rgb[1], rgb[2])
    return rgb
