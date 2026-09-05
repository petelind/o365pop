"""Twisted POP3 factory — cleartext USER/PASS, no STLS/APOP."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.credentials import IUsernamePassword
from twisted.cred.error import UnauthorizedLogin
from twisted.cred.portal import IRealm, Portal
from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.mail.pop3 import POP3, IMailbox
from zope.interface import implementer

from o365pop.accounts.store import verify_local_password
from o365pop.config import validate_bind
from o365pop.db import connect
from o365pop.mailstore.maildir import MaildirStore
from o365pop.popd.mailbox import MaildirPopMailbox

logger = logging.getLogger(__name__)


def run_popd(*, bind: str, port: int, maildir: Path, db_path: Path) -> None:
    """Start the Twisted reactor serving POP3.

    :param bind: Listen address. Example: ``"10.8.0.1"``
    :param port: Listen port. Example: ``110``
    :param maildir: Maildir root. Example: ``Path("var/maildir")``
    :param db_path: sqlite for local password. Example: ``Path("var/o365pop.sqlite3")``
    :return: None (blocks)
    :raises ValueError: if bind is empty
    """
    logger.info("popd.service.run_popd | entry | bind=%s port=%s", bind, port)
    allow_lan = _allow_lan_from_env()
    validate_bind(bind, allow_lan=allow_lan)
    logger.info("popd.service.run_popd | config | bind=%s port=%s", bind, port)
    factory = _build_factory(maildir, db_path)
    reactor.listenTCP(port, factory, interface=bind)
    logger.info("popd.service.run_popd | exit | listening=true bind=%s port=%s", bind, port)
    reactor.run(installSignalHandlers=False)


def _allow_lan_from_env() -> bool:
    """Read ALLOW_LAN from the process environment.

    :return: True when ALLOW_LAN is 1/true/TRUE. Example: ``False``
    """
    return os.getenv("ALLOW_LAN", "0") in ("1", "true", "TRUE")


def _build_factory(maildir: Path, db_path: Path) -> Factory:
    """Portal + POP3 factory (no TLS, no APOP challengers).

    :param maildir: Maildir root. Example: ``Path("var/maildir")``
    :param db_path: sqlite path. Example: ``Path("var/o365pop.sqlite3")``
    :return: Twisted factory. Example: ``<_POP3Factory>``
    """
    realm = _MailboxRealm(MaildirStore(maildir))
    portal = Portal(realm, [_LocalPasswordChecker(db_path)])
    factory = _POP3Factory(portal)
    logger.info("popd.service._build_factory | config | tls=false apop=false")
    return factory


class _CleartextPOP3(POP3):
    """POP3 dialect without APOP (cleartext USER/PASS only)."""

    def do_APOP(self, user, digest):  # noqa: N802 — Twisted command hook
        logger.info("popd.service._CleartextPOP3.do_APOP | branch | rejected=true")
        self.failResponse(b"APOP disabled")


class _POP3Factory(Factory):
    """Build a cleartext POP3 protocol bound to the local portal."""

    protocol = _CleartextPOP3
    noisy = False

    def __init__(self, portal: Portal) -> None:
        self.portal = portal

    def buildProtocol(self, addr):
        proto = _CleartextPOP3()
        proto.portal = self.portal
        proto.factory = self
        return proto


@implementer(IRealm)
class _MailboxRealm:
    """Return a MaildirPopMailbox avatar after successful USER/PASS."""

    def __init__(self, store: MaildirStore) -> None:
        self._store = store

    def requestAvatar(self, avatarId, mind, *interfaces):  # noqa: N802
        if IMailbox not in interfaces:
            raise NotImplementedError("IMailbox required")
        mailbox = MaildirPopMailbox(self._store)
        logger.info("popd.service._MailboxRealm.requestAvatar | exit | interface=IMailbox")
        return (IMailbox, mailbox, lambda: None)


@implementer(ICredentialsChecker)
class _LocalPasswordChecker:
    """Verify local mailbox USER/PASS. Never log the password."""

    credentialInterfaces = (IUsernamePassword,)

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def requestAvatarId(self, credentials):  # noqa: N802
        username = _as_text(credentials.username)
        password = _as_text(credentials.password)
        logger.info("popd.service._LocalPasswordChecker.requestAvatarId | entry | username=%s", username)
        conn = connect(self._db_path)
        try:
            matched = verify_local_password(conn, username, password)
        finally:
            conn.close()
        if not matched:
            logger.error(
                "popd.service._LocalPasswordChecker.requestAvatarId | error | reason=auth_failed username=%s",
                username,
            )
            raise UnauthorizedLogin()
        logger.info("popd.service._LocalPasswordChecker.requestAvatarId | exit | matched=true")
        return username.encode("utf-8")


def _as_text(value: bytes | str) -> str:
    """Decode a Twisted credential field.

    :param value: Username or password. Example: ``b"denis"``
    :return: Text. Example: ``"denis"``
    """
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value
