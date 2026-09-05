"""Public-client device-code login and bearer refresh (AUTH)."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime

from o365pop.accounts.ports import DeviceCodePort, MsalPort

logger = logging.getLogger(__name__)


class GraphAuthService:
    """Login, refresh, and bearer headers for the single mailbox.

    :param conn: sqlite connection. Example: ``connect(path)``
    :param encryption_key: Fernet key. Example: ``"gAAAAAB..."``
    :param device_code: Device-code port. Example: ``FixtureDeviceCode()``
    :param msal: Refresh port. Example: ``FixtureMsal()``
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        encryption_key: str,
        device_code: DeviceCodePort,
        msal: MsalPort,
    ) -> None:
        self._conn = conn
        self._key = encryption_key
        self._device_code = device_code
        self._msal = msal

    def login_device_code(self) -> str:
        """Run device-code login and persist encrypted tokens.

        :return: Username/UPN. Example: ``"denis@example.com"``
        :raises AuthenticationError: if login fails
        :raises ValueError: if encryption_key is missing
        """
        logger.info("GraphAuthService.login_device_code | entry")
        # 1. Validate encryption_key
        # 2. bundle = device_code.login()
        # 3. upsert_account + set tokens (never log token strings)
        # 4. Log exit user=upn
        raise NotImplementedError()

    def refresh_access_token(self) -> str:
        """Refresh an expired access token using the stored refresh token.

        :return: New access token. Example: ``"eyJ0..."``
        :raises AuthenticationError: if refresh is rejected
        """
        logger.info("GraphAuthService.refresh_access_token | entry")
        raise NotImplementedError()

    def ensure_bearer(self) -> str:
        """Return a valid access token, refreshing if expired.

        :return: Access token. Example: ``"eyJ0..."``
        :raises AuthenticationError: if no refresh token or refresh fails
        """
        logger.info("GraphAuthService.ensure_bearer | entry")
        # 1. If access valid → return
        # 2. Else refresh_access_token
        raise NotImplementedError()

    def is_access_valid(self, now: datetime | None = None) -> bool:
        """Whether stored access token expiry is in the future.

        :param now: Clock. Example: ``datetime.utcnow()``
        :return: True if still valid. Example: ``False``
        """
        logger.info("GraphAuthService.is_access_valid | entry")
        raise NotImplementedError()
