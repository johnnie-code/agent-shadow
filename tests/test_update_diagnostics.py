import os
import json
import shutil
import pytest
import subprocess
from unittest.mock import patch, MagicMock, AsyncMock
from shadow.core.config import SHADOW_HOME
from shadow.core.update_logger import UpdateLogger, get_update_history
from shadow.core.self_test import subsystem_runner, VerificationRunner, VerificationStep, VerificationResult
from shadow.cli.main import run_self_update_process, doctor
from rich.table import Table

@pytest.fixture(autouse=True)
def clean_update_logs():
    """Ensure clean update logs directory before each test."""
    log_dir = os.path.join(SHADOW_HOME, "logs", "update")
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)
    os.makedirs(log_dir, exist_ok=True)
    yield
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)

def test_update_logger_success():
    logger = UpdateLogger()
    logger.start_update("commit_before_123")
    logger.log_event("step_1", "Running step 1")
    logger.end_update(success=True, git_commit_after="commit_after_456")

    # Assert log file generated
    log_dir = os.path.join(SHADOW_HOME, "logs", "update")
    log_files = [f for f in os.listdir(log_dir) if f.endswith(".log")]
    assert len(log_files) == 1

    # Assert JSON summary generated
    json_files = [f for f in os.listdir(log_dir) if f.endswith(".json") and f != "history.json"]
    assert len(json_files) == 1

    # Verify summary contents
    with open(os.path.join(log_dir, json_files[0]), "r") as f:
        data = json.load(f)
        assert data["git_commit_before"] == "commit_before_123"
        assert data["git_commit_after"] == "commit_after_456"
        assert data["success"] is True

def test_update_logger_exception():
    logger = UpdateLogger()
    logger.start_update("commit_before_123")
    try:
        raise ValueError("Simulated dependency crash")
    except Exception as e:
        logger.log_exception("dependency_install", e)

    logger.end_update(success=False, git_commit_after="commit_before_123", rollback_reason="Simulated dependency crash")

    log_dir = os.path.join(SHADOW_HOME, "logs", "update")
    history = get_update_history()
    assert len(history) >= 1
    assert history[-1]["success"] is False
    assert "Simulated dependency crash" in history[-1]["failure_reason"]

def test_verification_runner_and_steps():
    runner = VerificationRunner()

    async def mock_pass_check():
        return True, "All systems nominal"

    async def mock_fail_check():
        return False, "Database disk full"

    runner.register_step("Pass Step", "Descr", mock_pass_check)
    runner.register_step("Fail Step", "Descr", mock_fail_check)

    # Run in event loop
    import asyncio
    report = asyncio.run(runner.run_all(fail_fast=False))

    assert report.success is False
    assert len(report.results) == 2
    assert report.results[0].success is True
    assert report.results[1].success is False
    assert report.results[1].message == "Database disk full"

# Note on patch argument mapping:
# The closest/bottommost decorator corresponds to the FIRST argument.
# Topmost decorator corresponds to the LAST argument.

@patch("subprocess.run") # topmost -> mock_run (6th argument)
@patch("subprocess.check_output") # mock_check_output (5th argument)
@patch("shadow.cli.main.daemon_restart") # mock_daemon_restart (4th argument)
@patch("shadow.cli.main.get_repo_dir") # mock_get_repo_dir (3rd argument)
@patch("shadow.cli.main.get_config") # mock_get_config (2nd argument)
@patch("shadow.core.self_test.subsystem_runner.run_all") # bottommost -> mock_run_all (1st argument)
def test_successful_self_update_flow(
    mock_run_all, mock_get_config, mock_get_repo_dir, mock_daemon_restart, mock_check_output, mock_run
):
    # Mocking configurations
    mock_cfg = MagicMock()
    mock_cfg.db_path = "/tmp/mock_shadow_db.db"
    mock_cfg.telegram_bot_token = None
    mock_cfg.telegram_chat_id = None
    mock_get_config.return_value = mock_cfg

    mock_get_repo_dir.return_value = "/mock/repo"
    mock_check_output.side_effect = lambda args, **kwargs: "mock_commit_123" if "rev-parse" in args else "pip-freeze-output"

    mock_run.return_value = MagicMock()
    mock_run.return_value.returncode = 0

    # Mocking VerificationRunner output
    mock_report = MagicMock()
    mock_report.success = True

    res1 = VerificationResult(step_name="Git Repository", success=True, message="Git healthy", execution_time_ms=1.0)
    res2 = VerificationResult(step_name="Database", success=True, message="DB healthy", execution_time_ms=1.0)
    mock_report.results = [res1, res2]
    mock_run_all.return_value = mock_report

    # Run the self update
    with patch("shutil.copy2") as mock_copy:
        run_self_update_process()

    # Verify success events were captured in logs
    history = get_update_history()
    assert len(history) >= 1
    assert history[-1]["success"] is True
    assert history[-1]["rollback"] is False

@patch("subprocess.run") # topmost -> mock_run (5th argument)
@patch("subprocess.check_output") # mock_check_output (4th argument)
@patch("shadow.cli.main.daemon_restart") # mock_daemon_restart (3rd argument)
@patch("shadow.cli.main.get_repo_dir") # mock_get_repo_dir (2nd argument)
@patch("shadow.cli.main.get_config") # bottommost -> mock_get_config (1st argument)
def test_failed_dependency_installation_rollback(
    mock_get_config, mock_get_repo_dir, mock_daemon_restart, mock_check_output, mock_run
):
    # Mocking configurations
    mock_cfg = MagicMock()
    mock_cfg.db_path = "/tmp/mock_shadow_db.db"
    mock_cfg.telegram_bot_token = None
    mock_cfg.telegram_chat_id = None
    mock_get_config.return_value = mock_cfg

    mock_get_repo_dir.return_value = "/mock/repo"
    mock_check_output.side_effect = lambda args, **kwargs: "mock_commit_123" if "rev-parse" in args else "pip-freeze-output"

    # Make subprocess run for pip install raise a CalledProcessError (simulating pip installation crash)
    def mock_run_side_effect(args, **kwargs):
        if "pip" in args or "install" in args:
            raise subprocess.CalledProcessError(1, args, stderr="Mock Wheel compilation error")
        mock_res = MagicMock()
        mock_res.returncode = 0
        return mock_res

    mock_run.side_effect = mock_run_side_effect

    # Run self update (which should trigger dependency crash and rollback)
    with patch("shutil.copy2") as mock_copy:
        run_self_update_process()

    # Verify update failed and rolled back
    history = get_update_history()
    assert len(history) >= 1
    assert history[-1]["success"] is False
    assert history[-1]["rollback"] is True
    assert "Dependency profile installation failed" in history[-1]["failure_reason"]

@patch("subprocess.run") # topmost -> mock_run (6th argument)
@patch("subprocess.check_output") # mock_check_output (5th argument)
@patch("shadow.cli.main.daemon_restart") # mock_daemon_restart (4th argument)
@patch("shadow.cli.main.get_repo_dir") # mock_get_repo_dir (3rd argument)
@patch("shadow.cli.main.get_config") # mock_get_config (2nd argument)
@patch("shadow.core.self_test.subsystem_runner.run_all") # bottommost -> mock_run_all (1st argument)
def test_failed_verification_causes_rollback_and_snapshot(
    mock_run_all, mock_get_config, mock_get_repo_dir, mock_daemon_restart, mock_check_output, mock_run
):
    # Mocking configurations
    mock_cfg = MagicMock()
    mock_cfg.db_path = "/tmp/mock_shadow_db.db"
    mock_cfg.telegram_bot_token = None
    mock_cfg.telegram_chat_id = None
    mock_get_config.return_value = mock_cfg

    mock_get_repo_dir.return_value = "/mock/repo"
    mock_check_output.side_effect = lambda args, **kwargs: "mock_commit_123" if "rev-parse" in args else "pip-freeze-output"

    mock_run.return_value = MagicMock()
    mock_run.return_value.returncode = 0

    # Simulate a verification check failure (e.g. CLI or Daemon verification failed)
    mock_report = MagicMock()
    mock_report.success = False

    failed_res = VerificationResult(
        step_name="CLI",
        success=False,
        message="Failed command: shadow mcp list. AttributeError: MCPManager has no attribute register_provider",
        execution_time_ms=5.0,
        error_message="AttributeError",
        traceback="Traceback:\nAttributeError: register_provider"
    )
    mock_report.results = [failed_res]
    mock_run_all.return_value = mock_report

    # Run self update
    with patch("shutil.copy2") as mock_copy:
        run_self_update_process()

    # Verify history logs failure
    history = get_update_history()
    assert len(history) >= 1
    assert history[-1]["success"] is False
    assert history[-1]["rollback"] is True
    assert "Verification failed" in history[-1]["failure_reason"]

    # Verify snapshot files were generated
    log_dir = os.path.join(SHADOW_HOME, "logs", "update")
    snapshots = [d for d in os.listdir(log_dir) if d.startswith("snapshot-")]
    assert len(snapshots) == 1

    snapshot_path = os.path.join(log_dir, snapshots[0])
    assert os.path.exists(os.path.join(snapshot_path, "environment.json"))
    assert os.path.exists(os.path.join(snapshot_path, "diagnostics.json"))

    with open(os.path.join(snapshot_path, "diagnostics.json"), "r") as f:
        meta = json.load(f)
        assert meta["failed_step"] == "verify_cli"
        assert "Verification failed on step 'CLI'" in meta["error_message"]

@patch("shadow.core.self_test.subsystem_runner.run_all")
def test_doctor_command_success(mock_run_all):
    mock_report = MagicMock()
    mock_report.success = True

    res = VerificationResult(step_name="Providers", success=True, message="AI providers online", execution_time_ms=2.0)
    mock_report.results = [res]
    mock_run_all.return_value = mock_report

    with patch("shadow.cli.main.console.print") as mock_print:
        doctor(repair=False)
        all_printed = []
        for call in mock_print.call_args_list:
            if call.args:
                all_printed.append(call.args[0])

        for arg in all_printed:
            print("MOCK ARG TYPE:", type(arg), "TITLE:", getattr(arg, "title", None))

        # Let's assert that there is a Table object printed or that the mock was called
        assert len(all_printed) >= 1
