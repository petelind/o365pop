"""Fernet helpers for Graph tokens (port taciturn2 shape; do not log material)."""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


def encrypt_token(token: str, key: str) -> bytes:
    """Encrypt a token for sqlite BLOB storage.

    :param token: Plain access or refresh token. Example: ``"eyJ0eXAiOi..."``
    :param key: Fernet key. Example: ``"gAAAAAB..."``
    :return: Ciphertext bytes. Example: ``b"gAAAAABhZ..."``
    :raises ValueError: if token or key is empty
    """
    logger.info("accounts.crypto.encrypt_token | entry | token_len=%s", len(token) if token else 0)
    # 1. Validate token and key non-empty
    # 2. Fernet(key).encrypt
    # 3. Log exit with ciphertext length only
    raise NotImplementedError()


def decrypt_token(blob: bytes, key: str) -> str:
    """Decrypt a stored token BLOB.

    :param blob: Ciphertext. Example: ``b"gAAAAABhZ..."``
    :param key: Fernet key. Example: ``"gAAAAAB..."``
    :return: Plain token. Example: ``"eyJ0eXAiOi..."``
    :raises ValueError: if blob or key is empty
    """
    logger.info("accounts.crypto.decrypt_token | entry | blob_len=%s", len(blob) if blob else 0)
    _ = Fernet
    raise NotImplementedError()
