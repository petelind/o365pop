"""Twisted IMailboxPOP3 adapter over MaildirStore."""

from __future__ import annotations

import logging
from io import BytesIO

from twisted.mail.pop3 import IMailbox
from zope.interface import implementer

from o365pop.mailstore.maildir import MaildirStore

logger = logging.getLogger(__name__)


@implementer(IMailbox)
class MaildirPopMailbox:
    """POP mailbox. DELE is local only — do not touch TossedMessage or Graph.

    :param store: Maildir store. Example: ``MaildirStore(Path("var/maildir"))``
    """

    def __init__(self, store: MaildirStore) -> None:
        self._store = store
        self._messages = list(store.list_uidls())
        self._deleted: set[int] = set()
        logger.info("MaildirPopMailbox.__init__ | config | count=%s", len(self._messages))

    def listMessages(self, index: int | None = None) -> int | list[int]:
        """Sizes, 0-based index.

        :param index: Message index or None. Example: ``0``
        :return: Size or list of sizes. Example: ``[240]``
        """
        logger.info("MaildirPopMailbox.listMessages | entry | index=%s", index)
        sizes = self._sizes()
        if index is None:
            logger.info("MaildirPopMailbox.listMessages | exit | count=%s", len(sizes))
            return sizes
        if index < 0 or index >= len(sizes):
            raise ValueError(index)
        logger.info("MaildirPopMailbox.listMessages | exit | size=%s", sizes[index])
        return sizes[index]

    def getMessage(self, index: int):
        """File-like RFC822 for RETR.

        :param index: 0-based. Example: ``0``
        :return: File object. Example: ``BytesIO(b"Subject: ...")``
        """
        logger.info("MaildirPopMailbox.getMessage | entry | index=%s", index)
        uidl = self._uidl_at(index)
        data = self._store.get(uidl)
        logger.info("MaildirPopMailbox.getMessage | exit | uidl=%s size=%s", uidl, len(data))
        return BytesIO(data)

    def getUidl(self, index: int) -> bytes:
        """UIDL bytes.

        :param index: 0-based. Example: ``0``
        :return: UIDL. Example: ``b"uid-outlook-1"``
        """
        logger.info("MaildirPopMailbox.getUidl | entry | index=%s", index)
        uidl = self._uidl_at(index)
        logger.info("MaildirPopMailbox.getUidl | exit | uidl=%s", uidl)
        return uidl.encode("ascii")

    def deleteMessage(self, index: int) -> None:
        """Mark local delete (sync on QUIT).

        :param index: 0-based. Example: ``0``
        :return: None
        """
        logger.info("MaildirPopMailbox.deleteMessage | entry | index=%s", index)
        self._uidl_at(index)
        self._deleted.add(index)
        logger.info("MaildirPopMailbox.deleteMessage | exit | marked=true index=%s", index)

    def undeleteMessages(self) -> None:
        """Undo DELE in this session.

        :return: None
        """
        logger.info("MaildirPopMailbox.undeleteMessages | entry")
        self._deleted.clear()
        logger.info("MaildirPopMailbox.undeleteMessages | exit | cleared=true")

    def sync(self) -> None:
        """Commit DELE to maildir. Do not delete TossedMessage.

        :return: None
        """
        logger.info("MaildirPopMailbox.sync | entry | pending=%s", len(self._deleted))
        for index in sorted(self._deleted):
            uidl, _size = self._messages[index]
            self._store.delete(uidl)
            logger.info("MaildirPopMailbox.sync | processing | uidl=%s", uidl)
        self._deleted.clear()
        logger.info("MaildirPopMailbox.sync | exit | status=ok")

    def _sizes(self) -> list[int]:
        """Octet sizes; deleted slots are 0.

        :return: Sizes. Example: ``[240, 0]``
        """
        return [0 if i in self._deleted else size for i, (_uidl, size) in enumerate(self._messages)]

    def _uidl_at(self, index: int) -> str:
        """UIDL for a live (not deleted) index.

        :param index: 0-based. Example: ``0``
        :return: UIDL. Example: ``"uid-outlook-1"``
        :raises ValueError: if index is out of range or deleted
        """
        if index < 0 or index >= len(self._messages) or index in self._deleted:
            raise ValueError(index)
        return self._messages[index][0]
