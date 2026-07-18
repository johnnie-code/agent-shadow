import pytest
import json
from shadow.core.mcp_manager import mcp_manager
from shadow.core.database import init_db
from shadow.tools.engine import unified_tool_engine
from shadow.core.events import event_bus

@pytest.mark.asyncio
async def test_mcp_manager_lifecycle():
    init_db()

    # 1. Install mock server (contains 'mock' in name to trigger simulated session)
    success = mcp_manager.install_server(
        name="test-mock-server",
        transport="stdio",
        command="python",
        args=["--version"],
        workspace="global",
        description="A great test MCP server"
    )
    assert success is True

    # 2. Get server info
    srv = mcp_manager.get_db_server("test-mock-server")
    assert srv is not None
    assert srv["transport"] == "stdio"

    # 3. Start server
    started = await mcp_manager.start_server("test-mock-server")
    assert started is True

    # 4. Check status
    srv = mcp_manager.get_db_server("test-mock-server")
    assert srv["status"] == "running"

    # 5. Disable and check status
    disabled = mcp_manager.disable_server("test-mock-server")
    assert disabled is True
    srv = mcp_manager.get_db_server("test-mock-server")
    assert srv["status"] == "disabled"

    # 6. Clean up
    removed = mcp_manager.remove_server("test-mock-server")
    assert removed is True
    assert mcp_manager.get_db_server("test-mock-server") is None

@pytest.mark.asyncio
async def test_mcp_permissions_and_execution():
    init_db()
    mcp_manager.install_server("exec-mock-server", "stdio")

    # Enable and start simulated (contains 'mock' in name)
    await mcp_manager.start_server("exec-mock-server")

    # Default permission check
    perm = mcp_manager.get_permission("exec-mock-server", "my_tool")
    assert perm == "Ask Every Time"

    # Update permission to Deny
    mcp_manager.set_permission("exec-mock-server", "my_tool", "Deny")
    perm = mcp_manager.get_permission("exec-mock-server", "my_tool")
    assert perm == "Deny"

    # Execute with Deny
    res = await mcp_manager.execute_tool("exec-mock-server", "my_tool", {})
    assert res["success"] is False
    assert "Denied" in res["error"]

    # Allow
    mcp_manager.set_permission("exec-mock-server", "my_tool", "Always Allow")
    res = await mcp_manager.execute_tool("exec-mock-server", "my_tool", {})
    assert res["success"] is True

    # Clean up
    mcp_manager.remove_server("exec-mock-server")

def test_unified_tool_resolution():
    # Resolve best tool for various task strings
    tool1 = unified_tool_engine.resolve_best_tool("Search for MEXT guidelines", "Find instructions on the web")
    assert tool1 == "web_search"

    tool2 = unified_tool_engine.resolve_best_tool("Read local configs")
    assert tool2 == "read_file"
