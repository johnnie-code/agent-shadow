import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch

from shadow.core.capabilities import (
    Capability,
    CapabilityRegistry,
    CapabilityScanner,
    CapabilityReport,
    CapabilityPlanner,
    capability_scanner,
    capability_planner,
    capability_registry
)
from shadow.core.runtime import ConversationEngine


@pytest.mark.asyncio
async def test_capability_registry():
    registry = CapabilityRegistry()
    cap = Capability(
        name="Test Tool",
        category="Native Tool",
        health="healthy",
        enabled=True,
        version="1.5",
        capabilities=["Do Stuff"],
        details={"desc": "A test tool capability"}
    )

    registry.register_capability(cap)
    assert len(registry.list_custom_capabilities()) == 1
    assert registry.get_capability("Test Tool").version == "1.5"

    registry.unregister_capability("Test Tool")
    assert len(registry.list_custom_capabilities()) == 0


@pytest.mark.asyncio
async def test_capability_scanner_discovery():
    scanner = CapabilityScanner()

    # Check scan_all builds the expected report structure
    report = await scanner.scan_all(force=True)
    assert "timestamp" in report
    assert "health" in report
    assert "sectors" in report

    sectors = report["sectors"]
    assert "ai_providers" in sectors
    assert "mcp_servers" in sectors
    assert "native_tools" in sectors
    assert "sandbox" in sectors
    assert "memory" in sectors
    assert "background_services" in sectors
    assert "apis" in sectors
    assert "plugins" in sectors


@pytest.mark.asyncio
async def test_health_scoring():
    scanner = CapabilityScanner()

    # Create test capabilities
    providers = [
        Capability(name="MockProvider", category="AI Provider", health="healthy", enabled=True),
        Capability(name="OpenAIProvider", category="AI Provider", health="offline", enabled=True)
    ]
    mcp_servers = []
    sandbox = Capability(name="Sandbox", category="Sandbox", health="healthy", enabled=True)
    memory = Capability(name="Memory", category="Memory", health="healthy", enabled=True)
    bg = Capability(name="Background", category="Background Service", health="healthy", enabled=True)

    bg.details["daemon"] = "running"
    bg.details["Telegram"] = "polling"

    health_info = scanner._calculate_overall_health(providers, mcp_servers, sandbox, memory, bg)

    # 1 configured provider is offline, overall score should reflect health penalties
    assert health_info.score < 100
    assert health_info.status in ("healthy", "degraded", "error")


@pytest.mark.asyncio
async def test_capability_report_formatting():
    scanner = CapabilityScanner()
    report_dict = await scanner.scan_all(force=True)

    summary = CapabilityReport.generate_health_summary(report_dict)
    assert "Overall Health" in summary
    assert "AI Providers" in summary
    assert "Sandbox" in summary
    assert "Memory" in summary


@pytest.mark.asyncio
async def test_capability_planner():
    planner = CapabilityPlanner()

    # Figma is not installed, so asking about Figma should suggest the Figma MCP server
    analysis = planner.analyze_missing_capability("Can you help me design in figma?")
    assert analysis is not None
    assert analysis["keyword"] == "figma"
    assert "Figma MCP Server" in analysis["suggested_config"]["name"]

    # If already installed (simulated), it shouldn't suggest it
    with patch("shadow.core.mcp_manager.mcp_manager.get_db_servers", return_value=[{"name": "figma"}]):
        analysis_installed = planner.analyze_missing_capability("Can you help me design in figma?")
        assert analysis_installed is None


@pytest.mark.asyncio
async def test_dynamic_conversation_response():
    engine = ConversationEngine()

    # Query asking for capabilities should return the live architectural capabilities report
    reply = await engine.chat("What can you do?")
    assert "PROJECT SHADOW — Live Architectural Capabilities Report" in reply
    assert "AI Core" in reply
    assert "Model Context Protocol" in reply
    assert "Sandbox" in reply

    # Query asking about figma should suggest the Figma MCP server from planner
    figma_reply = await engine.chat("I want to connect to Figma.")
    assert "I don't currently have an MCP server for Figma" in figma_reply
    assert "Figma MCP Server" in figma_reply


@pytest.mark.asyncio
async def test_automatic_refresh():
    scanner = CapabilityScanner()
    scanner.invalidate_cache()

    # First scan should populate cache
    report1 = await scanner.scan_all()
    assert report1 is not None

    # Second scan should hit cache
    report2 = await scanner.scan_all()
    assert report1["timestamp"] == report2["timestamp"]

    # Forcing should bypass cache
    await asyncio.sleep(0.01)
    report3 = await scanner.scan_all(force=True)
    assert report1["timestamp"] != report3["timestamp"]
