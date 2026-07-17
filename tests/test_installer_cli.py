import os
import shutil
import pytest
import subprocess
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from shadow.cli.main import app
from shadow.core.database import init_db
from shadow.core.config import SHADOW_HOME

runner = CliRunner()

@pytest.fixture(autouse=True)
def setup_test_db():
    from shadow.core.config import reset_config
    reset_config(None)
    init_db()

def test_doctor_command():
    from shadow.core.config import reset_config
    reset_config(None)
    # Test shadow doctor execution
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Doctor Diagnostics" in result.stdout
    assert "Shadow Doctor: All diagnostic checks passed" in result.stdout or "Completed checks" in result.stdout

def test_doctor_missing_mission():
    # Test doctor with missing mission.md (auto repairs/creates it)
    mission_path = os.path.join(SHADOW_HOME, "mission.md")
    if os.path.exists(mission_path):
        shutil.copy2(mission_path, mission_path + ".bak")
        os.remove(mission_path)

    try:
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "mission.md file is missing" in result.stdout
        assert "Creating a default mission.md" in result.stdout
        assert os.path.exists(mission_path)
    finally:
        # Restore backup
        if os.path.exists(mission_path + ".bak"):
            shutil.copy2(mission_path + ".bak", mission_path)
            os.remove(mission_path + ".bak")

@patch("subprocess.run")
def test_update_success(mock_run):
    # Mock subprocess.run for git pull, pip/uv install, pytest to return 0/success
    mock_run.return_value = MagicMock(returncode=0, stdout="Success")

    # Mock shutil.copy2 to prevent actual file copying during test, but verify it gets called
    with patch("shutil.copy2") as mock_copy, patch("os.makedirs") as mock_makedirs:
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0
        assert "Safe Self-Update System" in result.stdout
        assert "Creating automatic data backups" in result.stdout
        assert "Repository code successfully updated" in result.stdout
        assert "dependency profile updated successfully" in result.stdout
        assert "verification of all subsystems" in result.stdout
        assert "successfully updated" in result.stdout or "Update Completed Successfully!" in result.stdout

        # Verify backup copies were attempted
        assert mock_copy.call_count > 0

@patch("subprocess.run")
def test_update_failure_and_rollback(mock_run):
    # Mock subprocess.run to fail on git pull or dependencies install
    # Let's make git pull fail (returncode=1)
    mock_run.return_value = MagicMock(returncode=1, stderr="Git pull conflict")

    with patch("shutil.copy2") as mock_copy, patch("os.makedirs") as mock_makedirs, patch("shadow.cli.main.run_rollback") as mock_rollback:
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0
        assert "Git code update failed" in result.stdout
        # Full rollback is triggered on git failure to ensure safe state
        assert mock_rollback.call_count == 1

    # Let's mock git pull to succeed, but python dependency upgrade to fail
    def side_effect(cmd, *args, **kwargs):
        if "pull" in cmd or "rev-parse" in cmd or "fetch" in cmd:
            return MagicMock(returncode=0, stdout="Success")
        # Any other command (pip or uv) fails
        if kwargs.get("check"):
            raise subprocess.CalledProcessError(1, cmd, stderr="Failed dependency installation")
        return MagicMock(returncode=1, stderr="Failed dependency installation")

    mock_run.side_effect = side_effect

    with patch("shutil.copy2") as mock_copy, patch("os.makedirs") as mock_makedirs, patch("shadow.cli.main.run_rollback") as mock_rollback:
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0
        assert "Dependency profile installation failed" in result.stdout
        # Rollback should be called
        assert mock_rollback.call_count == 1

def test_uninstall_cancelled():
    # Test cancelling uninstall
    result = runner.invoke(app, ["uninstall"], input="n\n")
    assert result.exit_code == 0
    assert "Uninstallation cancelled" in result.stdout

@patch("shutil.rmtree")
@patch("os.remove")
@patch("os.path.exists")
def test_uninstall_preserve_data(mock_exists, mock_remove, mock_rmtree):
    # Test uninstall and preserve user data
    mock_exists.side_effect = lambda path: True if "venv" in path else False
    result = runner.invoke(app, ["uninstall"], input="y\ny\n")
    assert result.exit_code == 0
    assert "User data (database, config, mission.md) preserved" in result.stdout
    assert "Deleting virtual environment" in result.stdout
    assert "uninstalled successfully" in result.stdout

@patch("shutil.rmtree")
@patch("os.remove")
def test_uninstall_purge_data(mock_remove, mock_rmtree):
    # Test uninstall and remove/purge user data
    result = runner.invoke(app, ["uninstall"], input="y\nn\n")
    assert result.exit_code == 0
    assert "Removing user data" in result.stdout
    # Check that remove was called on database/env/mission
    assert mock_remove.call_count > 0
    assert "uninstalled successfully" in result.stdout
