"""BSP-07 — CLI status is the welcome/health surface (no HTTP)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from o365pop.accounts.ports import TokenBundle
from o365pop.cli import main


@pytest.mark.unit
def test_status_prints_healthy(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``python -m o365pop status`` reports healthy with SQLite and logging.

    :param tmp_path: Isolated workspace. Example: ``Path("/tmp/pytest-...")``
    :param capsys: Capture stdout
    :param monkeypatch: Env overrides
    :return: None
    """
    log_dir = tmp_path / "logs"
    data_dir = tmp_path / "var"
    monkeypatch.setenv("LOG_DIR", str(log_dir))
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("DB_PATH", str(data_dir / "o365pop.sqlite3"))
    monkeypatch.chdir(tmp_path)
    code = main(["status"])
    captured = capsys.readouterr()
    assert code == 0
    assert "healthy" in captured.out
    assert "SQLite" in captured.out
    assert "Celery" in captured.out
    assert (log_dir / "app.log").is_file()


@pytest.mark.unit
def test_login_without_encryption_key_exits_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """login refuses to run when TOKEN_ENCRYPTION_KEY is missing.

    :param monkeypatch: Env overrides
    :param tmp_path: Isolated workspace
    :param capsys: Capture stderr
    :return: None
    """
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "var"))
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "")
    monkeypatch.chdir(tmp_path)
    assert main(["login"]) == 1
    assert "TOKEN_ENCRYPTION_KEY" in capsys.readouterr().err


@pytest.mark.unit
def test_login_interactive_flag_uses_loopback_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--interactive`` stores tokens via the loopback port, not device-code.

    :param monkeypatch: Env and port stubs
    :param tmp_path: Isolated workspace
    :param capsys: Capture stdout
    :return: None
    """
    used: dict[str, bool] = {"interactive": False, "device": False}

    def fake_interactive(client_id: str, tenant_id: str):
        used["interactive"] = True
        return SimpleNamespace(
            login=lambda: TokenBundle(
                access_token="eyJ0-interactive",
                refresh_token="M.R3-interactive",
                expires_in=3600,
                username="denis@example.com",
                oid="00000000-0000-0000-0000-000000000001",
            )
        )

    def fake_device(client_id: str, tenant_id: str):
        used["device"] = True
        raise AssertionError("device-code must not run")

    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "var"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "var" / "o365pop.sqlite3"))
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", key)
    monkeypatch.setenv("AZURE_CLIENT_ID", "11111111-2222-3333-4444-555555555555")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("o365pop.cli.live_interactive_port", fake_interactive)
    monkeypatch.setattr("o365pop.cli.live_device_code_port", fake_device)
    assert main(["login", "--interactive"]) == 0
    assert used["interactive"] is True
    assert used["device"] is False
    assert "denis@example.com" in capsys.readouterr().out
