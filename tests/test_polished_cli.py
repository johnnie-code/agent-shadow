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

@patch("getpass.getpass", return_value="")
def test_settings_command_validation_loop(mock_getpass):
    inputs = [
        "3",            # Select Option 3: AI Provider
        "custom_prov",  # Invalid provider choice (Rich Prompt should reject)
        "ollama",       # Valid provider choice
        "4",            # Select Option 4: Notification Mode
        "custom_pref",  # Invalid preference choice (Rich Prompt should reject)
        "none",         # Valid preference choice
        "6",            # Select Option 6: Battery Saver Limit
        "abc",          # Invalid non-integer limit
        "120",          # Out of bounds limit (120 > 100)
        "50",           # Valid limit
        "7"             # Exit settings
    ]
    input_str = "\n".join(inputs) + "\n"
    try:
        result = runner.invoke(app, ["settings"], input=input_str)
        assert result.exit_code == 0
        assert "Please select one of the available options" in result.stdout
        assert "Successfully updated 'default_provider' to 'ollama'" in result.stdout
        assert "Successfully updated 'notification_preferences' to 'none'" in result.stdout
        assert "Error: Please enter a valid integer." in result.stdout
        assert "Error: Limit must be between 0 and 100." in result.stdout
        assert "Successfully updated 'battery_limit' to '50'" in result.stdout
        assert "Exiting settings menu" in result.stdout
    finally:
        # Clean up and reset modified configurations back to their original mock state
        from shadow.cli.main import config_set_env
        config_set_env("default_provider", "mock")
        config_set_env("notification_preferences", "terminal")
        config_set_env("battery_limit", "20")
