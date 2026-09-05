"""BSP-07 — CLI status is the welcome/health surface (no HTTP)."""

from __future__ import annotations

from pathlib import Path

import pytest

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
