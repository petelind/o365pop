"""POP1.2 — wrong password."""

from __future__ import annotations

import logging
import poplib
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.integration.test_pop_retrieve import POP_HOST, seed_local_mailbox, start_popd, stop_popd
from tests.support.log_story import assert_log_story
from tests.support.mailbox import MailboxSandbox

POP_AUTH_PORT = 11111


def _caplog_from_app_log(path: Path) -> SimpleNamespace:
    """Rebuild caplog-like records from the child process app.log.

    :param path: Log file. Example: ``Path("logs/app.log")``
    :return: Object with ``records``. Example: ``SimpleNamespace(records=[...])``
    """
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        level = logging.ERROR if " | error |" in line else logging.INFO
        record = logging.LogRecord("o365pop.popd.service", level, __file__, 0, line, None, None)
        records.append(record)
    return SimpleNamespace(records=records)


@pytest.mark.integration
@pytest.mark.log_story
def test_pop_wrong_password_is_rejected_without_logging_secret(sandbox: MailboxSandbox) -> None:
    """-ERR; password absent from logs.

    :return: None
    """
    seed_local_mailbox(sandbox)
    proc = start_popd(sandbox, POP_AUTH_PORT)
    try:
        client = poplib.POP3(POP_HOST, POP_AUTH_PORT, timeout=5)
        client.user("denis")
        with pytest.raises(poplib.error_proto) as exc_info:
            client.pass_("wrong")
        assert exc_info.value.args[0].startswith(b"-ERR")
        with pytest.raises(poplib.error_proto):
            client.retr(1)
        try:
            client.quit()
        except (poplib.error_proto, OSError):
            pass
    finally:
        stop_popd(proc)

    log_path = sandbox.log_dir / "app.log"
    auth_lines = [
        line
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if "requestAvatarId" in line or "verify_local_password" in line
    ]
    joined = "\n".join(auth_lines)
    assert "wrong" not in joined
    assert "local-pass" not in joined
    assert_log_story(
        _caplog_from_app_log(log_path),
        [
            {
                "where": "popd.service._LocalPasswordChecker.requestAvatarId",
                "beat": "error",
                "must_include": ["reason=auth_failed"],
                "level": "ERROR",
            }
        ],
    )
