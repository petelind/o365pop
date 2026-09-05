"""Load TFK-04 fixture files from ``tests/fixtures/``."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "fixtures"


def load_graph_case(case_id: str) -> Path:
    """Return the directory for a Graph fixture case.

    :param case_id: Catalog case id. Example: ``"SYNC1.1-outlook-q3-close"``
    :return: Case directory. Example: ``Path("tests/fixtures/graph/SYNC1.1-outlook-q3-close")``
    :raises FileNotFoundError: if the case directory is missing
    """
    path = FIXTURES_ROOT / "graph" / case_id
    logger.info("fixtures.load_graph_case | entry | case_id=%s", case_id)
    if not path.is_dir():
        raise FileNotFoundError(f"graph case not found: {path}")
    logger.info("fixtures.load_graph_case | exit | path=%s", path)
    return path


def load_graph_json(case_id: str, filename: str) -> dict[str, Any]:
    """Parse a JSON file from a Graph case.

    :param case_id: Catalog case id. Example: ``"SYNC1.3-empty"``
    :param filename: File name. Example: ``"inbox.json"``
    :return: Parsed object. Example: ``{"value": []}``
    :raises FileNotFoundError: if the file is missing
    :raises json.JSONDecodeError: if the file is not JSON
    """
    path = load_graph_case(case_id) / filename
    logger.info("fixtures.load_graph_json | entry | path=%s", path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    count = len(payload.get("value", [])) if isinstance(payload, dict) else None
    logger.info("fixtures.load_graph_json | exit | value_count=%s", count)
    return payload


def load_mail(mail_id: str) -> bytes:
    """Read an RFC822 fixture.

    :param mail_id: Stem under ``mail/``. Example: ``"hello-ada"``
    :return: MIME bytes. Example: ``b"From: Denis ..."``
    :raises FileNotFoundError: if the ``.eml`` is missing
    """
    path = FIXTURES_ROOT / "mail" / f"{mail_id}.eml"
    logger.info("fixtures.load_mail | entry | mail_id=%s", mail_id)
    if not path.is_file():
        raise FileNotFoundError(f"mail fixture not found: {path}")
    data = path.read_bytes()
    logger.info("fixtures.load_mail | exit | bytes=%s", len(data))
    return data


def load_preset(preset_id: str) -> dict[str, Any]:
    """Load a JSON table preset.

    :param preset_id: Stem under ``presets/``. Example: ``"empty"``
    :return: Tables dict. Example: ``{"mailbox_account": [], ...}``
    :raises FileNotFoundError: if the preset is missing
    """
    path = FIXTURES_ROOT / "presets" / f"{preset_id}.json"
    logger.info("fixtures.load_preset | entry | preset_id=%s", preset_id)
    if not path.is_file():
        raise FileNotFoundError(f"preset not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    logger.info("fixtures.load_preset | exit | tables=%s", list(payload))
    return payload
