import sys
import pytest
from typer.testing import CliRunner

def test_cli_starts_with_mcp_absent():
    # 1. Unload all shadow modules to ensure they are re-imported under the mock conditions
    for module_name in list(sys.modules.keys()):
        if "shadow" in module_name:
            del sys.modules[module_name]

    # 2. Prevent mcp from being imported by placing None in sys.modules
    mcp_modules = [
        "mcp",
        "mcp.server",
        "mcp.server.fastmcp",
        "mcp.server.sse",
        "mcp.client",
        "mcp.client.stdio",
        "mcp.client.sse",
    ]
    original_modules = {}
    for mod in mcp_modules:
        original_modules[mod] = sys.modules.get(mod)
        sys.modules[mod] = None

    try:
        # 3. Import shadow.core.mcp_manager and check that mcp_available is False
        from shadow.core.database import init_db
        init_db()

        from shadow.core.mcp_manager import mcp_available
        assert mcp_available is False

        # 4. Use Typer's CliRunner to invoke commands and ensure they don't crash
        from shadow.cli.main import app
        runner = CliRunner()

        # Test 'shadow status' command
        result_status = runner.invoke(app, ["status"])
        assert result_status.exit_code == 0, f"status command failed: {result_status.stdout}"

        # Test 'shadow health' command
        result_health = runner.invoke(app, ["health"])
        assert result_health.exit_code == 0, f"health command failed: {result_health.stdout}"

        # Test 'shadow version' command
        result_version = runner.invoke(app, ["version"])
        assert result_version.exit_code == 0, f"version command failed: {result_version.stdout}"

        # Test 'shadow chat' command help
        result_chat_help = runner.invoke(app, ["chat", "--help"])
        assert result_chat_help.exit_code == 0, f"chat help failed: {result_chat_help.stdout}"

    finally:
        # 5. Restore original sys.modules state
        for mod, val in original_modules.items():
            if val is None:
                if mod in sys.modules:
                    del sys.modules[mod]
            else:
                sys.modules[mod] = val

        # Clean up shadow imports again to restore normal environment for other tests
        for module_name in list(sys.modules.keys()):
            if "shadow" in module_name:
                del sys.modules[module_name]
