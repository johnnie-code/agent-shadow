import os
import pytest
from typer.testing import CliRunner
from shadow.cli.main import app
from shadow.core.config import SHADOW_HOME

runner = CliRunner()

@pytest.fixture(autouse=True)
def backup_restore_env():
    import shutil
    env_file = os.path.join(SHADOW_HOME, "config", ".env")
    backup_file = env_file + ".bak"
    has_backup = False
    if os.path.exists(env_file):
        shutil.move(env_file, backup_file)
        has_backup = True

    # Backup os.environ starting with SHADOW_
    env_backup = {k: v for k, v in os.environ.items() if k.startswith("SHADOW_")}

    # Clean up SHADOW_ variables for total isolation in this test file
    for k in list(os.environ.keys()):
        if k.startswith("SHADOW_") and k != "SHADOW_HOME":
            del os.environ[k]

    from shadow.core.config import reset_config
    reset_config(None)

    yield

    if has_backup:
        shutil.move(backup_file, env_file)
    elif os.path.exists(env_file):
        os.remove(env_file)

    # Restore os.environ starting with SHADOW_
    current_keys = [k for k in os.environ if k.startswith("SHADOW_")]
    for k in current_keys:
        del os.environ[k]
    for k, v in env_backup.items():
        os.environ[k] = v

    reset_config(None)

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

def test_settings_validation_provider():
    result = runner.invoke(app, ["settings"], input="3\ninvalid_provider\ngemini\n\n7\n")
    assert result.exit_code == 0
    assert "Error: Invalid provider selected." in result.stdout
    assert "Successfully updated 'default_provider' to 'gemini'" in result.stdout
    assert "Exiting settings menu" in result.stdout

def test_settings_validation_notifications():
    result = runner.invoke(app, ["settings"], input="4\ninvalid_mode\nnone\n7\n")
    assert result.exit_code == 0
    assert "Error: Invalid notification preferences." in result.stdout
    assert "Successfully updated 'notification_preferences' to 'none'" in result.stdout
    assert "Exiting settings menu" in result.stdout

def test_settings_validation_battery():
    result = runner.invoke(app, ["settings"], input="6\nabc\n105\n15\n7\n")
    assert result.exit_code == 0
    assert "Error: Battery Saver Limit must be a valid integer." in result.stdout
    assert "Error: Battery Saver Limit must be between 0 and 100." in result.stdout
    assert "Successfully updated 'battery_limit' to '15'" in result.stdout
    assert "Exiting settings menu" in result.stdout

def test_settings_api_key_indicators():
    from shadow.core.config import get_config, reset_config
    # Force default provider to openai and ensure key indicator says "Key Missing" (unless mock key is set/loaded from env)
    # First, test what happens when defaulting to mock
    os.environ["SHADOW_DEFAULT_PROVIDER"] = "mock"
    reset_config(None)
    config = get_config()
    try:
        # Exit settings immediately. Mock should not show Key Set/Missing
        result = runner.invoke(app, ["settings"], input="7\n")
        assert result.exit_code == 0
        assert "AI Provider:         mock" in result.stdout
        assert "Key Set" not in result.stdout
        assert "Key Missing" not in result.stdout

        # Change provider to openai (no key configured initially)
        # Note: we mock openai key to be empty
        os.environ["SHADOW_OPENAI__API_KEY"] = ""
        reset_config(None)
        config = get_config()
        try:
            # Choose option 3, set to openai, leave key empty, then exit
            result = runner.invoke(app, ["settings"], input="3\nopenai\n\n7\n")
            assert result.exit_code == 0
            # Next iteration displays openai with (Key Missing)
            assert "AI Provider:         openai (Key Missing)" in result.stdout
            assert "Enter OPENAI API Key" in result.stdout
            assert "already set" not in result.stdout
        finally:
            if "SHADOW_OPENAI__API_KEY" in os.environ:
                del os.environ["SHADOW_OPENAI__API_KEY"]
            reset_config(None)

        # Change provider to openai with key configured
        os.environ["SHADOW_OPENAI__API_KEY"] = "some_dummy_key"
        reset_config(None)
        config = get_config()
        try:
            # Option 3, set to openai. Prompt for key should show already set message. Press enter to keep current.
            result = runner.invoke(app, ["settings"], input="3\nopenai\n\n7\n")
            assert result.exit_code == 0
            assert "AI Provider:         openai (Key Set)" in result.stdout
            assert "Enter OPENAI API Key (already set, press Enter to keep current)" in result.stdout
        finally:
            if "SHADOW_OPENAI__API_KEY" in os.environ:
                del os.environ["SHADOW_OPENAI__API_KEY"]
            reset_config(None)

    finally:
        if "SHADOW_DEFAULT_PROVIDER" in os.environ:
            del os.environ["SHADOW_DEFAULT_PROVIDER"]
        reset_config(None)
