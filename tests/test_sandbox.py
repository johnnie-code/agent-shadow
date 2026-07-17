import os
import shutil
import pytest
import asyncio
import time
from shadow.core.config import SHADOW_HOME, get_config
from shadow.core.sandbox import sandbox_manager, SandboxComputer, job_manager
from shadow.core.sync import FileSyncManager
from shadow.core.browser import HeadlessBrowser, VisualDiffEngine
from shadow.core.android_sandbox import AndroidSandbox
from shadow.core.debugger import AutonomousDebugger
from shadow.tools.sandbox import SandboxExecuteTool
from shadow.core.plugins import plugin_registry, SandboxPlugin

@pytest.fixture(autouse=True)
def clean_sandbox_env():
    """Ensure a clean sandboxes test folder before and after each test."""
    sandboxes_dir = os.path.join(SHADOW_HOME, "sandboxes")
    if os.path.exists(sandboxes_dir):
        shutil.rmtree(sandboxes_dir)
    os.makedirs(sandboxes_dir, exist_ok=True)
    yield
    if os.path.exists(sandboxes_dir):
        shutil.rmtree(sandboxes_dir)


def test_sandbox_creation_and_destruction():
    sandbox_id = "test_env_1"
    computer = sandbox_manager.create_sandbox(sandbox_id, "python")

    assert computer.sandbox_id == sandbox_id
    assert computer.sandbox_type == "python"
    assert os.path.exists(computer.meta_path)
    assert os.path.exists(computer.notebook_path)

    # Check resource limits set
    meta = computer.load_meta()
    assert meta["sandbox_id"] == sandbox_id
    assert "cpu_timeout" in meta["resource_limits"]

    # Destroy
    success = sandbox_manager.destroy_sandbox(sandbox_id)
    assert success
    assert not os.path.exists(computer.sandbox_dir)


@pytest.mark.asyncio
async def test_command_execution_with_secrets_scrubbing():
    sandbox_id = "test_env_execute"
    computer = sandbox_manager.create_sandbox(sandbox_id, "generic")

    # Mocking some API key in config to verify scrubbing
    config = get_config()
    config.openai.api_key = "sk-12345secretkeyvalue"

    cmd = "echo 'My key is sk-12345secretkeyvalue'"
    res = await computer.execute_terminal(cmd)

    assert res["success"]
    assert "sk-12345secretkeyvalue" not in res["stdout"]
    assert "********" in res["stdout"]


@pytest.mark.asyncio
async def test_snapshot_and_restore():
    sandbox_id = "test_env_snapshots"
    computer = sandbox_manager.create_sandbox(sandbox_id, "node")

    # Write some files to workspace
    test_file_path = os.path.join(computer.workspace_dir, "app.js")
    with open(test_file_path, "w") as f:
        f.write("console.log('original');")

    # Capture snapshot
    success = sandbox_manager.snapshot_sandbox(sandbox_id, "initial_state")
    assert success

    # Overwrite file
    with open(test_file_path, "w") as f:
        f.write("console.log('modified');")

    # Restore snapshot
    success = sandbox_manager.restore_snapshot(sandbox_id, "initial_state")
    assert success

    # Verify original file content is restored
    with open(test_file_path, "r") as f:
        content = f.read()
    assert "original" in content


@pytest.mark.asyncio
async def test_real_git_state_operations():
    sandbox_id = "test_env_git"
    computer = sandbox_manager.create_sandbox(sandbox_id, "generic")

    # Run git init inside the isolated workspace
    res = await computer.git_op("init")
    assert res["success"]

    # Write a test file
    test_file = os.path.join(computer.workspace_dir, "README.md")
    with open(test_file, "w") as f:
        f.write("# Sandbox Project")

    # Git add and commit
    await computer.git_op("add", "README.md")
    commit_res = await computer.git_op("commit", "-m 'initial commit'")

    # Confirm git status or log is accessible and committed
    log_res = await computer.git_op("log", "--oneline")
    assert log_res["success"]
    assert "initial commit" in log_res["stdout"]


def test_parallel_sandboxes_isolation():
    # Create two sandboxes simultaneously
    sb1 = sandbox_manager.create_sandbox("env_parallel_1", "python")
    sb2 = sandbox_manager.create_sandbox("env_parallel_2", "node")

    # Write to workspace of sb1
    file_sb1 = os.path.join(sb1.workspace_dir, "test.txt")
    with open(file_sb1, "w") as f:
        f.write("sb1 data")

    # Write to workspace of sb2
    file_sb2 = os.path.join(sb2.workspace_dir, "test.txt")
    with open(file_sb2, "w") as f:
        f.write("sb2 data")

    # Confirm isolation of values
    with open(file_sb1, "r") as f:
        assert f.read() == "sb1 data"
    with open(file_sb2, "r") as f:
        assert f.read() == "sb2 data"

    # Listing sandboxes returns both correctly
    list_sb = sandbox_manager.list_sandboxes()
    ids = [s["sandbox_id"] for s in list_sb]
    assert "env_parallel_1" in ids
    assert "env_parallel_2" in ids


def test_security_isolation_path_traversal():
    computer = sandbox_manager.create_sandbox("security_test_env")

    # Attempting traversal to write outside the sandbox boundary
    with pytest.raises(PermissionError):
        computer.copy_file_to_sandbox("/etc/passwd", "../../../outside_traversal.txt")

    with pytest.raises(PermissionError):
        computer.sync_results_to_host("../../../outside_traversal.txt", "/tmp/host_test.txt")


@pytest.mark.asyncio
async def test_file_sync_and_conflict_detection():
    sandbox_id = "test_sync_conflicts"
    computer = sandbox_manager.create_sandbox(sandbox_id, "generic")

    # Create host relative mock file
    host_file = "mock_test_sync_file.txt"
    if os.path.exists(host_file):
        os.remove(host_file)

    with open(host_file, "w") as f:
        f.write("original production line")

    # Copy to sandbox
    computer.copy_file_to_sandbox(host_file, "mock_test_sync_file.txt")

    # Create local modification in sandbox
    ws_file = os.path.join(computer.workspace_dir, "mock_test_sync_file.txt")
    with open(ws_file, "w") as f:
        f.write("sandbox optimized line")

    # 1. Check change preview mtimes
    changes = FileSyncManager.preview_changes(sandbox_id)
    assert len(changes) == 1
    assert changes[0]["file"] == "mock_test_sync_file.txt"
    assert changes[0]["status"] == "modified"

    # 2. Modify host file after sandbox creation to trigger conflict check
    # We alter the host mtime artificially to trigger mtime check > sandbox creation time
    time.sleep(0.5)
    with open(host_file, "w") as f:
        f.write("host hotfix line")

    conflicts = FileSyncManager.detect_conflicts(sandbox_id)
    assert len(conflicts) == 1
    assert conflicts[0]["file"] == "mock_test_sync_file.txt"

    # Clean up host file
    if os.path.exists(host_file):
        os.remove(host_file)


@pytest.mark.asyncio
async def test_background_job_manager_lifecycle():
    sandbox_id = "test_env_jobs"
    computer = sandbox_manager.create_sandbox(sandbox_id, "generic")

    # Start an asynchronous background job
    job_id = job_manager.start_job(sandbox_id, "sleep 5")
    assert job_id.startswith("job_")

    # Query active job status
    status = job_manager.get_job_status(job_id)
    assert status["status"] == "running"
    assert status["command"] == "sleep 5"

    # Cancel/terminate background job
    cancelled = job_manager.cancel_job(job_id)
    assert cancelled

    status_after = job_manager.get_job_status(job_id)
    assert status_after["status"] in ["cancelled", "finished"]


@pytest.mark.asyncio
async def test_resource_limits_cpu_ram_tracking():
    sandbox_id = "test_env_limits"
    # Create with very tight memory limits to trigger termination immediately
    computer = sandbox_manager.create_sandbox(sandbox_id, "generic", resource_limits={
        "cpu_timeout": 30.0,
        "ram_limit_mb": 1, # 1 MB is incredibly small, should trigger RAM termination
        "disk_limit_mb": 1024
    })

    # Execute terminal command
    res = await computer.execute_terminal("echo 'test run'")
    # Usage metrics should compile successfully
    usage = computer.get_resource_usage()
    assert "storage_mb" in usage
    assert usage["cpu_percent"] >= 0.0


@pytest.mark.asyncio
async def test_headless_browser_fallbacks():
    browser = HeadlessBrowser()
    # Loading URL will fall back cleanly with status 200
    res = await browser.open_url("http://127.0.0.1:8000")
    assert res["success"]
    assert res["dom_length"] > 0

    # Test actions
    click_res = await browser.click_element("#login-btn")
    assert click_res["success"]

    await browser.fill_form("#username", "ghost-admin")
    logs = browser.capture_console_logs()
    assert any("ghost-admin" in l for l in logs)

    # Cleanup
    await browser.close()


def test_android_manifest_validation_and_compose_audit():
    # 1. Android Manifest Validation
    manifest_content = """<?xml version="1.0" encoding="utf-8"?>
    <manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.shadow.app">
        <uses-permission android:name="android.permission.INTERNET" />
        <application android:allowBackup="true">
            <activity android:name=".MainActivity">
                <intent-filter>
                    <action android:name="android.intent.action.MAIN" />
                    <category android:name="android.intent.category.LAUNCHER" />
                </intent-filter>
            </activity>
        </application>
    </manifest>
    """
    manifest_path = os.path.join(SHADOW_HOME, "AndroidManifest.xml")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_content)

    validation = AndroidSandbox.validate_manifest(manifest_path)
    assert validation["package_name"] == "com.shadow.app"
    assert "android.permission.INTERNET" in validation["permissions_found"]
    assert len(validation["issues"]) > 0
    assert not validation["success"]

    # 2. Compose Preview Sizing Audit
    compose_code = """
    @Composable
    fun HomeScreen() {
        Box(modifier = Modifier.size(150.dp).size(200.dp).size(50.dp).size(80.dp)) {
            Text("Test")
        }
    }
    """
    compose_path = os.path.join(SHADOW_HOME, "HomeScreen.kt")
    with open(compose_path, "w", encoding="utf-8") as f:
        f.write(compose_code)

    audit = AndroidSandbox.audit_compose_preview(compose_path)
    assert audit["has_composable"]
    assert not audit["has_preview"]
    assert len(audit["issues"]) > 0

    # Cleanup
    for p in [manifest_path, compose_path]:
        if os.path.exists(p):
            os.remove(p)


@pytest.mark.asyncio
async def test_autonomous_debugging_loop():
    sandbox_id = "test_env_debugger"
    computer = sandbox_manager.create_sandbox(sandbox_id, "python")

    broken_code = """
def run_app():
    prnt("Hello from broken Python script!")

run_app()
"""
    broken_file_path = os.path.join(computer.workspace_dir, "app.py")
    with open(broken_file_path, "w") as f:
        f.write(broken_code)

    res = await AutonomousDebugger.run_autonomous_fix_loop(
        computer,
        build_command="python -m py_compile app.py",
        test_command="python app.py",
        max_attempts=2
    )

    assert res["success"]
    assert res["attempts_taken"] == 2

    with open(broken_file_path, "r") as f:
        repaired_code = f.read()
    assert "print(" in repaired_code
    assert "prnt(" not in repaired_code


@pytest.mark.asyncio
async def test_sandbox_execute_tool_interface():
    tool = SandboxExecuteTool()
    assert tool.name == "sandbox_execute"
    assert tool.safety_level == 2

    # Test creating sandbox via tool
    res = await tool.execute(action="create", sandbox_id="tool_env", sandbox_type="node")
    assert res["success"]
    assert "created successfully" in res["result"]

    # Test updating notebook via tool
    res = await tool.execute(
        action="notebook_update",
        sandbox_id="tool_env",
        notebook_key="objective",
        notebook_value="Build modular chat"
    )
    assert res["success"]

    # Retrieve computer and verify AI notebook
    comp = sandbox_manager.get_sandbox("tool_env")
    assert comp is not None
    assert comp.load_notebook()["objective"] == "Build modular chat"

    # Test destroying sandbox via tool
    res = await tool.execute(action="destroy", sandbox_id="tool_env")
    assert res["success"]


def test_extensible_plugin_api_registration():
    # Define mock handler/plugin
    def custom_runtime_handler(cmd: str):
        return f"Rust compiled command: {cmd}"

    plugin_registry.register_runtime("rust", custom_runtime_handler)

    # Retrieve from registry
    handler = plugin_registry.get_runtime("rust")
    assert handler is not None
    assert handler("cargo run") == "Rust compiled command: cargo run"
