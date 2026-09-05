"""MSAL ports so AUTH tests never talk to live Microsoft."""

from __future__ import annotations

from typing import Protocol


class TokenBundle(dict):
    """Token result. Keys: access_token, refresh_token, expires_in, username, oid."""


class DeviceCodePort(Protocol):
    """Device-code login. Fixture in CI; MSAL in production."""

    def login(self) -> TokenBundle:
        """Complete device-code flow.

        :return: Tokens and username. Example: ``{"access_token": "eyJ0...", "username": "denis@example.com"}``
        :raises AuthenticationError: if Microsoft rejects the flow
        """
        ...


class MsalPort(Protocol):
    """Refresh and silent acquire."""

    def refresh(self, refresh_token: str) -> TokenBundle:
        """Exchange a refresh token.

        :param refresh_token: Stored refresh token. Example: ``"M.R3..."``
        :return: New bundle. Example: ``{"access_token": "eyJ0...", "expires_in": 3600}``
        :raises AuthenticationError: if refresh is rejected
        """
        ...
