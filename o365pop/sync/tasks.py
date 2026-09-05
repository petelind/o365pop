"""Celery tasks: AUTH stub first; SYNC/SMTP/TEAM extend (do not add a second mailbox task)."""

from __future__ import annotations

import logging

from o365pop.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="o365pop.sync.sync_mailbox")
def sync_mailbox(self) -> dict:
    """Ensure bearer then (later) pull+toss. Auth fail → failed session, no retry.

    :return: Result dict. Example: ``{"status": "failed", "error": "auth_failed"}``
    """
    logger.info("sync.tasks.sync_mailbox | entry | task_id=%s", getattr(self.request, "id", None))
    # 1. start_session
    # 2. ensure_bearer — AUTH1.3: AuthenticationError → mark_failed, return, do not raise
    # 3. SYNC: list inbox+chats, toss, mark_completed
    raise NotImplementedError()


@celery_app.task(bind=True, name="o365pop.sync.scan_outbound_spool")
def scan_outbound_spool(self) -> dict:
    """SMTP/TEAM: scan spool and sendMail or post chat.

    :return: Result dict. Example: ``{"status": "completed", "sent": 1}``
    """
    logger.info("sync.tasks.scan_outbound_spool | entry | task_id=%s", getattr(self.request, "id", None))
    raise NotImplementedError()
