import os
import shutil
import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from shadow.cli.main import app
from shadow.core.config import SHADOW_HOME, get_config

runner = CliRunner()

@pytest.fixture(autouse=True)
def backup_restore_env():
    """Backup and restore the .env file on disk to prevent state leakage."""
    env_dir = os.path.join(SHADOW_HOME, "config")
    env_file = os.path.join(env_dir, ".env")
    env_bak = os.path.join(env_dir, ".env.bak")

    has_env = os.path.exists(env_file)
    if has_env:
        shutil.copy2(env_file, env_bak)

    yield

    if has_env:
        if os.path.exists(env_bak):
            shutil.copy2(env_bak, env_file)
            os.remove(env_bak)
    else:
        if os.path.exists(env_file):
            os.remove(env_file)

def test_settings_user_assistant_names():
    # Option 1: Edit user profile name, Option 2: Edit assistant name, Option 7: Exit
    inputs = "1\nNewUserName\n2\nNewAssistantName\n7\n"
    result = runner.invoke(app, ["settings"], input=inputs)
    assert result.exit_code == 0
    assert "PROJECT SHADOW SETTINGS INTERFACE" in result.stdout
    assert "Successfully updated 'user_name' to 'NewUserName'" in result.stdout
    assert "Successfully updated 'assistant_name' to 'NewAssistantName'" in result.stdout

def test_settings_ai_provider_shortcut():
    # Option 3: AI Provider, select 1 (mock), then exit
    inputs = "3\n1\n7\n"
    result = runner.invoke(app, ["settings"], input=inputs)
    assert result.exit_code == 0
    assert "AI Provider" in result.stdout
    assert "Successfully updated 'default_provider' to 'mock'" in result.stdout

@patch("shadow.cli.main.test_openai_connectivity")
def test_settings_ai_provider_openai_with_test(mock_test_openai):
    mock_test_openai.return_value = MagicMock()
    # Option 3: AI Provider, select 2 (openai), api key: dummy_key, test connectivity: yes (y), exit
    inputs = "3\n2\ndummy_key\ny\n7\n"
    result = runner.invoke(app, ["settings"], input=inputs)
    assert result.exit_code == 0
    assert "Successfully updated 'default_provider' to 'openai'" in result.stdout
    assert "Testing OPENAI..." in result.stdout

def test_settings_notification_mode_shortcut():
    # Option 4: Notification preferences, select 3 (none), then exit
    inputs = "4\n3\n7\n"
    result = runner.invoke(app, ["settings"], input=inputs)
    assert result.exit_code == 0
    assert "Successfully updated 'notification_preferences' to 'none'" in result.stdout
