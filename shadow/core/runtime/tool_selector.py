from typing import Dict, Any, Optional
from shadow.core.capabilities import capability_scanner
from shadow.core.runtime.executor_registry import executor_registry, BaseExecutor
from shadow.tools.engine import unified_tool_engine
from shadow.core.logging import logger

class ToolSelector:
    def __init__(self):
        pass

    async def select_tool_for_task(self, task_title: str, task_description: str) -> Optional[str]:
        # Dynamically inspect capabilities
        scan = await capability_scanner.scan_all(force=True)
        sectors = scan["sectors"]

        task_title_lower = task_title.lower()
        task_desc_lower = task_description.lower()

        # HTML generation or creation
        if "html" in task_title_lower or "web page" in task_title_lower:
            return "code_executor"

        # GitHub search or integration
        if "github" in task_title_lower or "github" in task_desc_lower:
            # Check if GitHub MCP is running
            mcp_servers = sectors.get("mcp_servers", [])
            github_mcp_active = any(m.name.lower() == "github" and m.health == "healthy" for m in mcp_servers)
            if github_mcp_active:
                return "mcp_executor"
            else:
                return "code_executor"

        # Web / Firecrawl Scraping / Docs
        if "scrape" in task_title_lower or "crawl" in task_title_lower or "firecrawl" in task_title_lower:
            return "web_executor"

        # Headless Playwright browser / JS page
        if "javascript" in task_title_lower or "js page" in task_title_lower or "playwright" in task_title_lower:
            return "browser_executor"

        # Memory operation
        if "memory" in task_title_lower or "remember" in task_title_lower:
            return "memory_executor"

        # Filesystem
        if "file" in task_title_lower or "write" in task_title_lower or "save" in task_title_lower or "create css" in task_title_lower:
            return "filesystem_executor"

        # Let unified_tool_engine resolve best native/MCP tool
        resolved = unified_tool_engine.resolve_best_tool(task_title, task_description)
        if resolved:
            if "." in resolved:
                return "mcp_executor"
            return "filesystem_executor"

        # Default fallback
        return "code_executor"
