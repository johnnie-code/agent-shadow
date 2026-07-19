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

def test_settings_command_exit():
    result = runner.invoke(app, ["settings"], input="7\n")
    assert result.exit_code == 0
    assert "Exiting settings menu" in result.stdout

def test_settings_command_update_and_exit():
    result = runner.invoke(app, ["settings"], input="1\nPaletteTestUser\n7\n")
    assert result.exit_code == 0
    assert "Successfully updated 'user_name' to 'PaletteTestUser'" in result.stdout
    assert "Exiting settings menu" in result.stdout

def test_settings_command_ai_provider_validation():
    local_runner = CliRunner()
    # Input 3 (AI Provider), then invalid "invalid_provider", then valid "gemini", then skip api key, then exit (7)
    result = local_runner.invoke(app, ["settings"], input="3\ninvalid_provider\ngemini\n\n7\n")
    assert result.exit_code == 0
    assert "Invalid AI Provider" in result.stdout
    assert "Successfully updated 'default_provider' to 'gemini'" in result.stdout

def test_settings_command_notification_validation():
    local_runner = CliRunner()
    # Input 4 (Notification Mode), then invalid "popup", then valid "none", then exit (7)
    result = local_runner.invoke(app, ["settings"], input="4\npopup\nnone\n7\n")
    assert result.exit_code == 0
    assert "Invalid Notification Mode" in result.stdout
    assert "Successfully updated 'notification_preferences' to 'none'" in result.stdout

def test_settings_command_battery_validation():
    local_runner = CliRunner()
    # Input 6 (Battery Limit), then invalid "-5", then invalid "120", then invalid "abc", then valid "15", then exit (7)
    result = local_runner.invoke(app, ["settings"], input="6\n-5\n120\nabc\n15\n7\n")
    assert result.exit_code == 0
    assert "Invalid Battery Saver Limit" in result.stdout
    assert "Successfully updated 'battery_limit' to '15'" in result.stdout
