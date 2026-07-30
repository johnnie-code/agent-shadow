import os
import pytest
from typer.testing import CliRunner
from shadow.core.config import SHADOW_HOME

runner = CliRunner()

@pytest.fixture(autouse=True)
def backup_restore_env():
    import shutil
    import os
    env_file = os.path.join(SHADOW_HOME, "config", ".env")
    backup_file = env_file + ".bak"
    has_backup = False
    if os.path.exists(env_file):
        shutil.copy2(env_file, backup_file)
        has_backup = True

    # Backup SHADOW_ env vars
    orig_env = {k: v for k, v in os.environ.items() if k.startswith("SHADOW_")}

    yield

    # Restore SHADOW_ env vars
    current_shadow_keys = [k for k in os.environ if k.startswith("SHADOW_")]
    for k in current_shadow_keys:
        if k not in orig_env:
            del os.environ[k]
    for k, v in orig_env.items():
        os.environ[k] = v

    if has_backup:
        shutil.move(backup_file, env_file)
    elif os.path.exists(env_file):
        os.remove(env_file)
    import sys
    config_module = sys.modules.get("shadow.core.config")
    if config_module:
        config_module.reset_config(None)

def test_version_command():
    from shadow.cli.main import app
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Shadow OS" in result.stdout
    assert "Version" in result.stdout
    assert "Platform" in result.stdout

def test_diagnostics_command():
    from shadow.cli.main import app
    result = runner.invoke(app, ["diagnostics"])
    assert result.exit_code == 0
    assert "Running Diagnostics" in result.stdout

def test_repair_command():
    from shadow.cli.main import app
    result = runner.invoke(app, ["repair"])
    assert result.exit_code == 0
    assert "Shadow Auto-Repair" in result.stdout

def test_runtime_command():
    from shadow.cli.main import app
    result = runner.invoke(app, ["runtime", "status"])
    assert result.exit_code == 0
    assert "Autonomous Runtime" in result.stdout

def test_telegram_command_not_configured():
    from shadow.cli.main import app
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
    from shadow.cli.main import app
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
    from shadow.cli.main import app
    result = runner.invoke(app, ["settings"], input="7\n")
    assert result.exit_code == 0
    assert "Exiting settings menu" in result.stdout

def test_settings_command_update_and_exit():
    from shadow.cli.main import app
    result = runner.invoke(app, ["settings"], input="1\nPaletteTestUser\n7\n")
    assert result.exit_code == 0
    assert "Successfully updated 'user_name' to 'PaletteTestUser'" in result.stdout
    assert "Exiting settings menu" in result.stdout

def test_settings_validation_provider():
    from shadow.cli.main import app
    result = runner.invoke(app, ["settings"], input="3\ninvalid_provider\ngemini\n\n7\n")
    assert result.exit_code == 0
    assert "Error: Invalid provider selected." in result.stdout
    assert "Successfully updated 'default_provider' to 'gemini'" in result.stdout
    assert "Exiting settings menu" in result.stdout

def test_settings_validation_notifications():
    from shadow.cli.main import app
    result = runner.invoke(app, ["settings"], input="4\ninvalid_mode\nnone\n7\n")
    assert result.exit_code == 0
    assert "Error: Invalid notification preferences." in result.stdout
    assert "Successfully updated 'notification_preferences' to 'none'" in result.stdout
    assert "Exiting settings menu" in result.stdout

def test_settings_validation_battery():
    from shadow.cli.main import app
    result = runner.invoke(app, ["settings"], input="6\nabc\n105\n15\n7\n")
    assert result.exit_code == 0
    assert "Error: Battery Saver Limit must be a valid integer." in result.stdout
    assert "Error: Battery Saver Limit must be between 0 and 100." in result.stdout
    assert "Successfully updated 'battery_limit' to '15'" in result.stdout
    assert "Exiting settings menu" in result.stdout

def test_settings_api_key_presence_and_safeguards():
    import os
    import sys
    # Force reload of main and config to avoid any stale references
    if "shadow.cli.main" in sys.modules:
        del sys.modules["shadow.cli.main"]
    if "shadow.core.config" in sys.modules:
        del sys.modules["shadow.core.config"]
    from shadow.cli.main import app, config_set_env

    # Ensure gemini has no key initially and default_provider is gemini
    config_set_env("default_provider", "gemini")
    os.environ["SHADOW_DEFAULT_PROVIDER"] = "gemini"
    # To clear gemini API key from env and on-disk config:
    env_file = os.path.join(SHADOW_HOME, "config", ".env")
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            lines = f.readlines()
        new_lines = [l for l in lines if not l.startswith("SHADOW_GEMINI__API_KEY=")]
        with open(env_file, "w") as f:
            f.writelines(new_lines)
    if "SHADOW_GEMINI__API_KEY" in os.environ:
        del os.environ["SHADOW_GEMINI__API_KEY"]

    config_module = sys.modules.get("shadow.core.config")
    if config_module:
        config_module.reset_config(None)

    # Run settings menu to verify (Key Missing) is shown
    result = runner.invoke(app, ["settings"], input="7\n")
    assert result.exit_code == 0
    assert "gemini (Key Missing)" in result.stdout

    # Now let's set a key using settings option 3
    result = runner.invoke(app, ["settings"], input="3\ngemini\nMY_SECRET_KEY\n7\n")
    assert result.exit_code == 0
    assert "Successfully updated 'default_provider' to 'gemini'" in result.stdout

    # Run settings menu to verify (Key Set) is shown, and prompting keep current works
    result2 = runner.invoke(app, ["settings"], input="3\ngemini\n\n7\n")
    assert result2.exit_code == 0
    assert "gemini (Key Set)" in result2.stdout
    assert "Enter GEMINI API Key (already set, press Enter to keep current)" in result2.stdout

    # Verify key was not cleared by hitting Enter
    if config_module:
        config_module.reset_config(None)
    cfg = config_module.get_config() if config_module else None
    assert cfg is not None
    assert cfg.gemini.api_key == "MY_SECRET_KEY"
