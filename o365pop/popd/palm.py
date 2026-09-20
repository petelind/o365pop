"""Palm POP view: serve prebuilt maildir-palm; DELE records palm-deleted.json."""

from __future__ import annotations

import logging

from o365pop.mailstore.maildir import MaildirStore
from o365pop.popd.mailbox import MaildirPopMailbox
from o365pop.tosser.palm_view import load_hidden_uidls, save_hidden_uidls

logger = logging.getLogger(__name__)


class PalmPublishedMailbox(MaildirPopMailbox):
    """Serve published Palm files. DELE is local to maildir-palm."""

    def __init__(self, store: MaildirStore) -> None:
        super().__init__(store)
        self._hidden = load_hidden_uidls(store.root)
        logger.info(
            "popd.palm.PalmPublishedMailbox.__init__ | config | count=%s hidden=%s",
            len(self._messages),
            len(self._hidden),
        )

    def sync(self) -> None:
        """Delete Palm files and persist hashes so publish does not restore them.

        :return: None
        """
        for index in sorted(self._deleted):
            uidl, _size = self._messages[index]
            self._hidden.add(uidl)
        save_hidden_uidls(self._store.root, self._hidden)
        logger.info(
            "popd.palm.PalmPublishedMailbox.sync | exit | hidden=%s pending=%s",
            len(self._hidden),
            len(self._deleted),
        )
        super().sync()
