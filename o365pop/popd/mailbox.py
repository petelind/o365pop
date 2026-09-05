"""Twisted IMailboxPOP3 adapter over MaildirStore."""

from __future__ import annotations

import logging

from o365pop.mailstore.maildir import MaildirStore

logger = logging.getLogger(__name__)


class MaildirPopMailbox:
    """POP mailbox. DELE is local only — do not touch TossedMessage or Graph.

    :param store: Maildir store. Example: ``MaildirStore(Path("var/maildir"))``
    """

    def __init__(self, store: MaildirStore) -> None:
        self._store = store

    def listMessages(self, index: int | None = None) -> int | list[int]:
        """Sizes, 0-based index.

        :param index: Message index or None. Example: ``0``
        :return: Size or list of sizes. Example: ``[240]``
        """
        logger.info("MaildirPopMailbox.listMessages | entry | index=%s", index)
        raise NotImplementedError()

    def getMessage(self, index: int):
        """File-like RFC822 for RETR.

        :param index: 0-based. Example: ``0``
        :return: File object. Example: ``BytesIO(b"Subject: ...")``
        """
        logger.info("MaildirPopMailbox.getMessage | entry | index=%s", index)
        raise NotImplementedError()

    def getUidl(self, index: int) -> bytes:
        """UIDL bytes.

        :param index: 0-based. Example: ``0``
        :return: UIDL. Example: ``b"uid-outlook-1"``
        """
        logger.info("MaildirPopMailbox.getUidl | entry | index=%s", index)
        raise NotImplementedError()

    def deleteMessage(self, index: int) -> None:
        """Mark local delete (sync on QUIT).

        :param index: 0-based. Example: ``0``
        :return: None
        """
        logger.info("MaildirPopMailbox.deleteMessage | entry | index=%s", index)
        raise NotImplementedError()

    def undeleteMessages(self) -> None:
        """Undo DELE in this session.

        :return: None
        """
        logger.info("MaildirPopMailbox.undeleteMessages | entry")
        raise NotImplementedError()

    def sync(self) -> None:
        """Commit DELE to maildir. Do not delete TossedMessage.

        :return: None
        """
        logger.info("MaildirPopMailbox.sync | entry")
        raise NotImplementedError()
