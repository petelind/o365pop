"""Fernet helpers for Graph tokens (port taciturn2 shape; do not log material)."""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def encrypt_token(token: str, key: str) -> bytes:
    """Encrypt a token for sqlite BLOB storage.

    :param token: Plain access or refresh token. Example: ``"eyJ0eXAiOi..."``
    :param key: Fernet key. Example: ``"gAAAAAB..."``
    :return: Ciphertext bytes. Example: ``b"gAAAAABhZ..."``
    :raises ValueError: if token or key is empty
    """
    logger.info("accounts.crypto.encrypt_token | entry | token_len=%s", len(token) if token else 0)
    _validate_token_and_key(token, key)
    ciphertext = Fernet(_key_bytes(key)).encrypt(token.encode("utf-8"))
    logger.info("accounts.crypto.encrypt_token | exit | blob_len=%s", len(ciphertext))
    return ciphertext


def decrypt_token(blob: bytes, key: str) -> str:
    """Decrypt a stored token BLOB.

    :param blob: Ciphertext. Example: ``b"gAAAAABhZ..."``
    :param key: Fernet key. Example: ``"gAAAAAB..."``
    :return: Plain token. Example: ``"eyJ0eXAiOi..."``
    :raises ValueError: if blob or key is empty
    """
    logger.info("accounts.crypto.decrypt_token | entry | blob_len=%s", len(blob) if blob else 0)
    if not blob:
        raise ValueError("token blob must not be empty")
    if not key:
        raise ValueError("encryption key must not be empty")
    try:
        plain = Fernet(_key_bytes(key)).decrypt(blob).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        logger.error("accounts.crypto.decrypt_token | error | reason=decrypt_failed")
        raise ValueError("token blob could not be decrypted") from exc
    logger.info("accounts.crypto.decrypt_token | exit | token_len=%s", len(plain))
    return plain


def _validate_token_and_key(token: str, key: str) -> None:
    """Reject empty token or key material.

    :param token: Plain token. Example: ``"eyJ0..."``
    :param key: Fernet key. Example: ``"gAAAAAB..."``
    :return: None
    :raises ValueError: if either value is empty
    """
    if not token:
        raise ValueError("token must not be empty")
    if not key:
        raise ValueError("encryption key must not be empty")


def _key_bytes(key: str) -> bytes:
    """Encode a Fernet key string.

    :param key: ASCII Fernet key. Example: ``"gAAAAAB..."``
    :return: Key bytes. Example: ``b"gAAAAAB..."``
    """
    return key.encode("ascii") if isinstance(key, str) else key
