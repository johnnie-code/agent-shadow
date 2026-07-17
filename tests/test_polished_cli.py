import os
import pytest
from typer.testing import CliRunner
from shadow.cli.main import app
from shadow.core.config import SHADOW_HOME

runner = CliRunner()

def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Shadow OS" in result.stdout
    assert "Version" in result.stdout
    assert "Platform" in result.stdout

def test_diagnostics_command():
    result = runner.invoke(app, ["diagnostics"])
    assert result.exit_code == 0
    assert "Running Diagnostics" in result.stdout

def test_repair_command():
    result = runner.invoke(app, ["repair"])
    assert result.exit_code == 0
    assert "Shadow Auto-Repair" in result.stdout

def test_runtime_command():
    result = runner.invoke(app, ["runtime", "status"])
    assert result.exit_code == 0
    assert "Autonomous Runtime" in result.stdout

def test_telegram_command_not_configured():
    from shadow.core.config import get_config
    cfg = get_config()
    orig_token = cfg.telegram_bot_token
    cfg.telegram_bot_token = None
    try:
        result = runner.invoke(app, ["telegram", "status"])
        assert "NOT CONFIGURED" in result.stdout
    finally:
        cfg.telegram_bot_token = orig_token

def test_config_command():
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0

from unittest.mock import patch, MagicMock

@patch("httpx.get")
def test_check_github_upgrade(mock_get):
    from shadow.cli.main import check_github_upgrade
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '[project]\nversion = "1.2.0"'
    mock_get.return_value = mock_resp

    with patch("rich.console.Console.print") as mock_print:
        check_github_upgrade()
        printed_texts = "".join([call[0][0] for call in mock_print.call_args_list if isinstance(call[0][0], str)])
        assert "A newer version of Shadow OS is available" in printed_texts
