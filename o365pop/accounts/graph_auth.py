"""Public-client device-code login and bearer refresh (AUTH)."""

from __future__ import annotations

import logging
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import msal

from o365pop.accounts.errors import AuthenticationError
from o365pop.accounts.ports import DeviceCodePort, MsalPort, TokenBundle
from o365pop.accounts.store import (
    _get_password_hash,
    _hash_local_password,
    get_account,
    get_encrypted_access_token,
    get_encrypted_refresh_token,
    set_encrypted_access_token,
    set_encrypted_refresh_token,
    set_token_expires_at,
    upsert_account,
)

logger = logging.getLogger(__name__)

# offline_access is reserved — MSAL adds it automatically.
GRAPH_SCOPES = (
    "Mail.Read",
    "Mail.ReadWrite",
    "Mail.Send",
    "Chat.ReadWrite",
    "User.Read",
    "Tasks.ReadWrite",
    "Calendars.ReadWrite",
    "MailboxSettings.Read",
)
_EXPIRY_SKEW = timedelta(seconds=60)
_DEVICE_FLOW_TIMEOUT_SECONDS = 30
LOOPBACK_PORT = 8400
LOOPBACK_REDIRECT = f"http://localhost:{LOOPBACK_PORT}"


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
        self._require_key()
        bundle = self._device_code.login()
        username = self._persist_bundle(bundle)
        logger.info("GraphAuthService.login_device_code | exit | user=%s", username)
        return username

    def refresh_access_token(self) -> str:
        """Refresh an expired access token using the stored refresh token.

        :return: New access token. Example: ``"eyJ0..."``
        :raises AuthenticationError: if refresh is rejected
        """
        logger.info("GraphAuthService.refresh_access_token | entry")
        self._require_key()
        refresh = get_encrypted_refresh_token(self._conn, self._key)
        if not refresh:
            logger.error("GraphAuthService.refresh_access_token | error | reason=auth_failed")
            raise AuthenticationError("refresh_token_missing")
        try:
            bundle = self._msal.refresh(refresh)
        except AuthenticationError:
            logger.error("GraphAuthService.refresh_access_token | error | reason=auth_failed")
            raise
        access = str(bundle.get("access_token") or "")
        if not access:
            logger.error("GraphAuthService.refresh_access_token | error | reason=auth_failed")
            raise AuthenticationError("refresh_token_rejected")
        self._store_access(bundle, access)
        logger.info("GraphAuthService.refresh_access_token | exit | token_len=%s", len(access))
        return access

    def ensure_bearer(self) -> str:
        """Return a valid access token, refreshing if expired.

        :return: Access token. Example: ``"eyJ0..."``
        :raises AuthenticationError: if no refresh token or refresh fails
        """
        logger.info("GraphAuthService.ensure_bearer | entry")
        if self.is_access_valid():
            access = get_encrypted_access_token(self._conn, self._key)
            if access:
                logger.info("GraphAuthService.ensure_bearer | branch | refresh=false")
                logger.info("GraphAuthService.ensure_bearer | exit | refreshed=false")
                return access
        logger.info("GraphAuthService.ensure_bearer | branch | refresh=true")
        access = self.refresh_access_token()
        logger.info("GraphAuthService.ensure_bearer | exit | refreshed=true")
        return access

    def is_access_valid(self, now: datetime | None = None) -> bool:
        """Whether stored access token expiry is in the future.

        :param now: Clock. Example: ``datetime.utcnow()``
        :return: True if still valid. Example: ``False``
        """
        logger.info("GraphAuthService.is_access_valid | entry")
        account = get_account(self._conn)
        clock = now or datetime.now(UTC)
        if clock.tzinfo is None:
            clock = clock.replace(tzinfo=UTC)
        expires = account.token_expires_at if account else None
        if expires is not None and expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        valid = expires is not None and expires - _EXPIRY_SKEW > clock
        logger.info("GraphAuthService.is_access_valid | exit | valid=%s", valid)
        return valid

    def _require_key(self) -> None:
        """Fail fast when TOKEN_ENCRYPTION_KEY is missing.

        :return: None
        :raises ValueError: if the key is empty
        """
        if not self._key:
            raise ValueError("TOKEN_ENCRYPTION_KEY is required")

    def _persist_bundle(self, bundle: TokenBundle) -> str:
        """Write identity + encrypted tokens from a login bundle.

        :param bundle: Port result. Example: ``{"username": "denis@example.com", ...}``
        :return: Username. Example: ``"denis@example.com"``
        :raises AuthenticationError: if tokens or username are missing
        """
        username = str(bundle.get("username") or "")
        access = str(bundle.get("access_token") or "")
        refresh = str(bundle.get("refresh_token") or "")
        oid = str(bundle.get("oid") or "")
        if not username or not access or not refresh:
            logger.error("GraphAuthService.login_device_code | error | reason=auth_failed")
            raise AuthenticationError("device_code_rejected")
        existing = get_account(self._conn)
        mailbox_user = existing.mailbox_user if existing and existing.mailbox_user else username.split("@")[0]
        password_hash = _get_password_hash(self._conn) or _hash_local_password("")
        upsert_account(
            self._conn,
            display_name=username,
            graph_user_id=oid,
            mailbox_user=mailbox_user,
            mailbox_password_hash=password_hash,
        )
        set_encrypted_access_token(self._conn, access, self._key)
        set_encrypted_refresh_token(self._conn, refresh, self._key)
        self._store_expiry(bundle)
        return username

    def _store_access(self, bundle: TokenBundle, access: str) -> None:
        """Persist a refreshed access token and optional new refresh token.

        :param bundle: Refresh result. Example: ``{"access_token": "eyJ0...", "expires_in": 3600}``
        :param access: New access token. Example: ``"eyJ0..."``
        :return: None
        """
        set_encrypted_access_token(self._conn, access, self._key)
        new_refresh = str(bundle.get("refresh_token") or "")
        if new_refresh:
            set_encrypted_refresh_token(self._conn, new_refresh, self._key)
        self._store_expiry(bundle)

    def _store_expiry(self, bundle: TokenBundle) -> None:
        """Set token_expires_at from expires_in seconds.

        :param bundle: Token result. Example: ``{"expires_in": 3600}``
        :return: None
        """
        raw = bundle.get("expires_in", 3600)
        try:
            seconds = int(raw)
        except (TypeError, ValueError):
            seconds = 3600
        set_token_expires_at(self._conn, datetime.now(UTC) + timedelta(seconds=seconds))


def live_device_code_port(client_id: str, tenant_id: str) -> DeviceCodePort:
    """MSAL public-client device-code port (production).

    :param client_id: Azure app id. Example: ``"11111111-2222-3333-4444-555555555555"``
    :param tenant_id: Tenant or common. Example: ``"common"``
    :return: Port with ``login``. Example: ``SimpleNamespace(login=...)``
    """
    return SimpleNamespace(login=lambda: _msal_device_login(client_id, tenant_id))


def live_interactive_port(client_id: str, tenant_id: str) -> DeviceCodePort:
    """MSAL loopback PKCE port (operator Mac; work tenants block device-code).

    :param client_id: Azure app id. Example: ``"11111111-2222-3333-4444-555555555555"``
    :param tenant_id: Tenant or common. Example: ``"common"``
    :return: Port with ``login``. Example: ``SimpleNamespace(login=...)``
    """
    return SimpleNamespace(login=lambda: _msal_interactive_login(client_id, tenant_id))


def live_msal_port(client_id: str, tenant_id: str) -> MsalPort:
    """MSAL refresh port (production).

    :param client_id: Azure app id. Example: ``"11111111-2222-3333-4444-555555555555"``
    :param tenant_id: Tenant or common. Example: ``"common"``
    :return: Port with ``refresh``. Example: ``SimpleNamespace(refresh=...)``
    """
    return SimpleNamespace(refresh=lambda token: _msal_refresh(client_id, tenant_id, token))


def _public_app(client_id: str, tenant_id: str) -> msal.PublicClientApplication:
    """Build a public MSAL client.

    :param client_id: Azure app id. Example: ``"11111111-2222-3333-4444-555555555555"``
    :param tenant_id: Tenant or common. Example: ``"common"``
    :return: MSAL app. Example: ``PublicClientApplication(...)``
    """
    authority = f"https://login.microsoftonline.com/{tenant_id or 'common'}"
    return msal.PublicClientApplication(client_id, authority=authority)


def _msal_device_login(client_id: str, tenant_id: str) -> TokenBundle:
    """Run MSAL device-code flow. Prints the user code; never logs tokens.

    :param client_id: Azure app id. Example: ``"11111111-2222-3333-4444-555555555555"``
    :param tenant_id: Tenant or common. Example: ``"common"``
    :return: Token bundle. Example: ``{"username": "denis@example.com", ...}``
    :raises AuthenticationError: if Microsoft rejects the flow
    """
    logger.info("accounts.graph_auth._msal_device_login | entry | tenant=%s", tenant_id)
    if not client_id:
        raise AuthenticationError("azure_client_id_missing")
    app = _public_app(client_id, tenant_id)
    flow = _initiate_device_flow(app)
    emit_device_code_prompt(flow)
    result = app.acquire_token_by_device_flow(flow)
    bundle = _bundle_from_msal(result, flow="device_code")
    logger.info("accounts.graph_auth._msal_device_login | exit | user=%s", bundle.get("username"))
    return bundle


def _msal_interactive_login(client_id: str, tenant_id: str) -> TokenBundle:
    """Run MSAL loopback PKCE. Opens a browser; never logs tokens.

    :param client_id: Azure app id. Example: ``"11111111-2222-3333-4444-555555555555"``
    :param tenant_id: Tenant or common. Example: ``"common"``
    :return: Token bundle. Example: ``{"username": "denis@example.com", ...}``
    :raises AuthenticationError: if Microsoft rejects the flow
    """
    logger.info("accounts.graph_auth._msal_interactive_login | entry | tenant=%s", tenant_id)
    if not client_id:
        raise AuthenticationError("azure_client_id_missing")
    app = _public_app(client_id, tenant_id)
    sys.stderr.write(
        "\n=== Microsoft interactive login ===\n"
        f"Opening a browser (redirect {LOOPBACK_REDIRECT}).\n"
        "Sign in and accept Mail.Read, Mail.ReadWrite, Mail.Send, Chat.ReadWrite, User.Read, "
        "Tasks.ReadWrite, MailboxSettings.Read.\n\n"
    )
    sys.stderr.flush()
    result = app.acquire_token_interactive(scopes=list(GRAPH_SCOPES), port=LOOPBACK_PORT)
    bundle = _bundle_from_msal(result, flow="interactive")
    logger.info("accounts.graph_auth._msal_interactive_login | exit | user=%s", bundle.get("username"))
    return bundle


def emit_device_code_prompt(flow: dict) -> None:
    """Write URL + user code to stderr. Never log the code.

    :param flow: MSAL device-flow dict. Example: ``{"user_code": "ABCD1234", "verification_uri": "https://microsoft.com/link"}``
    :return: None
    :raises AuthenticationError: if user_code is missing
    """
    uri = str(flow.get("verification_uri") or "https://www.microsoft.com/link")
    code = str(flow.get("user_code") or "")
    if not code:
        logger.error("accounts.graph_auth.emit_device_code_prompt | error | reason=missing_user_code")
        raise AuthenticationError("device_code_rejected")
    sys.stderr.write(
        "\n=== Microsoft device-code login ===\n"
        f"1. Open: {uri}\n"
        f"2. Enter code: {code}\n"
        "3. Sign in as the mailbox user within 15 minutes.\n\n"
    )
    sys.stderr.flush()


def _initiate_device_flow(app: msal.PublicClientApplication) -> dict:
    """Ask Microsoft for a device code; fail if the HTTP call hangs.

    :param app: Public MSAL client. Example: ``PublicClientApplication(...)``
    :return: Flow dict. Example: ``{"user_code": "ABCD1234", "verification_uri": "https://microsoft.com/link"}``
    :raises AuthenticationError: on timeout or missing user_code
    """
    logger.info("accounts.graph_auth._initiate_device_flow | entry")
    sys.stderr.write("Requesting a device code from Microsoft (up to 30s)…\n")
    sys.stderr.flush()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(app.initiate_device_flow, scopes=list(GRAPH_SCOPES))
        try:
            flow = future.result(timeout=_DEVICE_FLOW_TIMEOUT_SECONDS)
        except TimeoutError:
            logger.error("accounts.graph_auth._initiate_device_flow | error | reason=timeout")
            sys.stderr.write(
                "Microsoft did not return a device code in 30s. "
                "Check network / AZURE_CLIENT_ID, then re-run: make test-e2e\n"
            )
            sys.stderr.flush()
            raise AuthenticationError("device_code_timeout") from None
    if not isinstance(flow, dict) or "user_code" not in flow:
        logger.error("accounts.graph_auth._initiate_device_flow | error | reason=rejected")
        raise AuthenticationError("device_code_rejected")
    logger.info("accounts.graph_auth._initiate_device_flow | exit | status=ok")
    return flow


def _msal_refresh(client_id: str, tenant_id: str, refresh_token: str) -> TokenBundle:
    """Exchange a refresh token via MSAL.

    :param client_id: Azure app id. Example: ``"11111111-2222-3333-4444-555555555555"``
    :param tenant_id: Tenant or common. Example: ``"common"``
    :param refresh_token: Stored refresh token. Example: ``"M.R3..."``
    :return: Token bundle. Example: ``{"access_token": "eyJ0...", "expires_in": 3600}``
    :raises AuthenticationError: if refresh is rejected
    """
    logger.info("accounts.graph_auth._msal_refresh | entry")
    app = _public_app(client_id, tenant_id)
    result = app.acquire_token_by_refresh_token(refresh_token, scopes=list(GRAPH_SCOPES))
    bundle = _bundle_from_msal(result, flow="refresh")
    logger.info("accounts.graph_auth._msal_refresh | exit | has_access=%s", bool(bundle.get("access_token")))
    return bundle


def _bundle_from_msal(result: dict, *, flow: str = "refresh") -> TokenBundle:
    """Map an MSAL result dict to TokenBundle; raise on error.

    :param result: MSAL result. Example: ``{"access_token": "eyJ0...", "id_token_claims": {...}}``
    :param flow: ``device_code``, ``interactive``, or ``refresh``. Example: ``"interactive"``
    :return: Token bundle. Example: ``{"username": "denis@example.com", ...}``
    :raises AuthenticationError: if MSAL returned an error
    """
    if not result or result.get("error") or not result.get("access_token"):
        reason = _failure_reason(flow)
        msal_error = str((result or {}).get("error") or "empty")
        description = str((result or {}).get("error_description") or "")
        logger.error(
            "accounts.graph_auth._bundle_from_msal | error | reason=%s msal_error=%s",
            reason,
            msal_error,
        )
        _emit_login_failure(flow, msal_error, description)
        raise AuthenticationError(reason)
    claims = result.get("id_token_claims") or {}
    username = str(claims.get("preferred_username") or claims.get("upn") or result.get("username") or "")
    return TokenBundle(
        access_token=result.get("access_token", ""),
        refresh_token=result.get("refresh_token", ""),
        expires_in=int(result.get("expires_in") or 3600),
        username=username,
        oid=str(claims.get("oid") or ""),
    )


def _failure_reason(flow: str) -> str:
    """Map an MSAL flow name to AuthenticationError text.

    :param flow: ``device_code``, ``interactive``, or ``refresh``. Example: ``"interactive"``
    :return: Reason. Example: ``"login_rejected"``
    """
    if flow == "refresh":
        return "refresh_token_rejected"
    if flow == "device_code":
        return "device_code_rejected"
    return "login_rejected"


def _emit_login_failure(flow: str, msal_error: str, description: str) -> None:
    """Write a safe stderr hint. Never include tokens.

    :param flow: MSAL path. Example: ``"interactive"``
    :param msal_error: Azure error code. Example: ``"invalid_grant"``
    :param description: Azure description. Example: ``"AADSTS65001: ..."``
    :return: None
    """
    hint = description.split("\r")[0].split("\n")[0][:240]
    if flow == "interactive":
        sys.stderr.write(
            f"Interactive login failed ({msal_error}). {hint}\n"
            "If this is AADSTS65001, add Mail.Read, Mail.ReadWrite, Mail.Send, Chat.ReadWrite, "
            "Tasks.ReadWrite, MailboxSettings.Read "
            "on the Azure app and retry python -m o365pop login --interactive.\n"
        )
    elif flow == "device_code":
        sys.stderr.write(
            f"Device-code login failed ({msal_error}). "
            "Work tenants often block this; use: python -m o365pop login --interactive\n"
        )
    sys.stderr.flush()
