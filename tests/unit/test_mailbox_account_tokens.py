"""AUTH1.1 — Fernet vault; no plaintext tokens in sqlite."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_encrypt_token_roundtrip_returns_original() -> None:
    """encrypt then decrypt yields the same token string.

    :return: None
    """
    raise NotImplementedError()


@pytest.mark.unit
def test_set_encrypted_access_token_does_not_store_plaintext() -> None:
    """sqlite BLOB must not contain the raw token.

    :return: None
    """
    raise NotImplementedError()


@pytest.mark.unit
def test_set_encrypted_access_token_with_empty_string_clears_field() -> None:
    """Empty token stores NULL / missing.

    :return: None
    """
    raise NotImplementedError()
