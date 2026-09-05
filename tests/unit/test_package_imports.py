"""BOOT1.1 — installable package and bounded-context modules import."""

from __future__ import annotations

import importlib

import pytest

PACKAGE_MODULES = (
    "o365pop",
    "o365pop.config",
    "o365pop.db",
    "o365pop.celery_app",
    "o365pop.cli",
    "o365pop.logging_setup",
    "o365pop.accounts",
    "o365pop.graph",
    "o365pop.tosser",
    "o365pop.mailstore",
    "o365pop.popd",
    "o365pop.smtpd",
    "o365pop.sync",
)


@pytest.mark.unit
@pytest.mark.parametrize("module_name", PACKAGE_MODULES)
def test_package_module_imports(module_name: str) -> None:
    """Each SAO §3 package module imports without error.

    :param module_name: Dotted module. Example: ``"o365pop.tosser"``
    :return: None
    """
    module = importlib.import_module(module_name)
    assert module is not None


@pytest.mark.unit
def test_package_version_present() -> None:
    """Package exposes a version string.

    :return: None
    """
    import o365pop

    assert o365pop.__version__ == "0.1.0"
