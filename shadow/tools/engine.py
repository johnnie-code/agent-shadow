import json
from typing import Dict, Any, List, Optional
from shadow.tools.registry import tool_registry
from shadow.core.mcp_manager import mcp_manager
from shadow.core.logging import log_decision

class MCPToolAdapter:
    """
    Adapter that makes an MCP tool appear identical to a native Shadow Tool.
    """
    def __init__(self, server_name: str, tool_name: str, description: str = "", schema: Optional[Dict[str, Any]] = None):
        self._server_name = server_name
        self._tool_name = tool_name
        self._description = description or f"MCP tool '{tool_name}' on server '{server_name}'"
        self._schema = schema or {}

    @property
    def name(self) -> str:
        return f"{self._server_name}.{self._tool_name}"

    @property
    def description(self) -> str:
        return self._description

    @property
    def safety_level(self) -> int:
        # MCP tool safety can be resolved based on user permissions config
        perm = mcp_manager.get_permission(self._server_name, self._tool_name)
        if perm == "Deny":
            return 3 # Restricted
        elif perm in ("Always Allow", "Allow Once"):
            return 0 # Safe/Automatic
        else:
            return 2 # Requires manual/human confirmation/hold

    @property
    def schema(self) -> Dict[str, Any]:
        return self._schema

    async def execute(self, **kwargs) -> Dict[str, Any]:
        return await mcp_manager.execute_tool(self._server_name, self._tool_name, kwargs)


class UnifiedToolEngine:
    """
    Central hub for managing, discovering, and executing tools from both
    native implementations and external MCP servers.
    """
    def get_tool(self, name: str) -> Optional[Any]:
        """
        Get a tool by name. Supports native tools (e.g., 'read_file')
        and MCP tools (e.g., 'github.open_repo').
        """
        # 1. Native Tool check
        native_tool = tool_registry.get_tool(name)
        if native_tool:
            return native_tool

        from shadow.core.mcp_manager import mcp_available
        if not mcp_available:
            return None

        # 2. MCP Tool check
        if "." in name:
            parts = name.split(".", 1)
            server_name, tool_name = parts[0], parts[1]
            server = mcp_manager.get_db_server(server_name)
            if server:
                # Retrieve tools metadata
                try:
                    tools_list = json.loads(server["tools"] or "[]")
                    if tool_name in tools_list:
                        return MCPToolAdapter(server_name, tool_name)
                except Exception:
                    pass

        # Also support finding tool in any active server if matching
        servers = mcp_manager.get_db_servers()
        for s in servers:
            try:
                tools_list = json.loads(s["tools"] or "[]")
                if name == f"{s['name']}.{name}":
                    return MCPToolAdapter(s['name'], name)
                if name in tools_list:
                    return MCPToolAdapter(s['name'], name)
            except Exception:
                pass

        return None

    def list_tools(self, workspace: Optional[str] = None) -> List[Any]:
        """
        List all available native and workspace-scoped MCP tools.
        """
        all_tools = []
        # Add native
        all_tools.extend(tool_registry.list_tools())

        from shadow.core.mcp_manager import mcp_available
        if not mcp_available:
            return all_tools

        # Add registered MCP tools
        servers = mcp_manager.get_db_servers(workspace)
        for s in servers:
            try:
                tools_list = json.loads(s["tools"] or "[]")
                for t in tools_list:
                    all_tools.append(MCPToolAdapter(s["name"], t))
            except Exception:
                pass

        return all_tools

    def resolve_best_tool(self, task_title: str, task_description: str = "", workspace: Optional[str] = None) -> str:
        """
        Autonomous tool resolution: maps task descriptions/titles to the most
        appropriate native or MCP tool, fully automating the integration.
        """
        text = f"{task_title} {task_description}".lower()

        from shadow.core.mcp_manager import mcp_available
        if mcp_available:
            # Workspace scoped overrides first
            # E.g., Notion integration
            if "notion" in text:
                # Check if Notion MCP is installed
                servers = mcp_manager.get_db_servers(workspace)
                for s in servers:
                    if "notion" in s["name"].lower():
                        try:
                            tools = json.loads(s["tools"] or "[]")
                            # Return first matching tool
                            if tools:
                                return f"{s['name']}.{tools[0]}"
                        except Exception:
                            pass

            # E.g., GitHub integration
            if "github" in text or "repo" in text:
                servers = mcp_manager.get_db_servers(workspace)
                for s in servers:
                    if "github" in s["name"].lower() or "git" in s["name"].lower():
                        try:
                            tools = json.loads(s["tools"] or "[]")
                            # e.g., open_repo or create_issue
                            for t in tools:
                                if "open" in t or "create" in t:
                                    return f"{s['name']}.{t}"
                            if tools:
                                return f"{s['name']}.{tools[0]}"
                        except Exception:
                            pass

            # E.g., Firecrawl or Fetch integration
            if "documentation" in text or "search docs" in text or "fetch" in text or "firecrawl" in text:
                servers = mcp_manager.get_db_servers(workspace)
                for s in servers:
                    if any(x in s["name"].lower() for x in ("firecrawl", "fetch", "brave", "search")):
                        try:
                            tools = json.loads(s["tools"] or "[]")
                            if tools:
                                return f"{s['name']}.{tools[0]}"
                        except Exception:
                            pass

            # Standard Fallbacks
            if "search" in text or "query" in text:
                # Check if Brave Search or Google Search MCP is installed
                servers = mcp_manager.get_db_servers(workspace)
                for s in servers:
                    if "brave" in s["name"].lower() or "search" in s["name"].lower():
                        try:
                            tools = json.loads(s["tools"] or "[]")
                            if tools:
                                return f"{s['name']}.{tools[0]}"
                        except Exception:
                            pass
                return "web_search"

        else:
            if "search" in text or "query" in text:
                return "web_search"

        return "read_file"

# Global Unified Tool Engine Singleton
unified_tool_engine = UnifiedToolEngine()
