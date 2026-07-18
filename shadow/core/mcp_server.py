import os
from typing import List, Dict, Any

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.server.sse import SseServerTransport
    mcp_available = True
except ImportError:
    mcp_available = False
    FastMCP = None
    SseServerTransport = None

from starlette.applications import Starlette
from starlette.routing import Mount, Route
from shadow.core.database import get_db_connection
from shadow.tools.registry import tool_registry

if mcp_available:
    # Create FastMCP server
    mcp_server = FastMCP(
        "ShadowServer",
        instructions="Exposes Shadow OS Tools, Goals, Opportunities, and Memories over MCP."
    )
else:
    mcp_server = None

# Define Resources

def get_shadow_goals() -> str:
    """Retrieve current active goals and projects tracked by Shadow OS."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM goals WHERE status = 'pending' OR status = 'active'")
    rows = cursor.fetchall()
    conn.close()

    goals = [dict(r) for r in rows]
    import json
    return json.dumps(goals, indent=2)

if mcp_server is not None:
    mcp_server.resource("shadow://goals")(get_shadow_goals)


def get_shadow_opportunities() -> str:
    """Retrieve newly discovered opportunities."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM opportunities WHERE status = 'new'")
    rows = cursor.fetchall()
    conn.close()

    opps = [dict(r) for r in rows]
    import json
    return json.dumps(opps, indent=2)

if mcp_server is not None:
    mcp_server.resource("shadow://opportunities")(get_shadow_opportunities)


def get_shadow_memories() -> str:
    """Retrieve relevant memories."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM memory ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    res = [dict(r) for r in rows]

    import json
    return json.dumps(res, indent=2)

if mcp_server is not None:
    mcp_server.resource("shadow://memories")(get_shadow_memories)


# Define Tools

async def read_file(filepath: str) -> str:
    """Reads a file in the workspace or repository root."""
    tool = tool_registry.get_tool("read_file")
    if not tool:
        return "Error: Native read_file tool not registered."
    res = await tool.execute(filepath=filepath)
    if res.get("success"):
        return str(res["result"])
    return f"Error: {res.get('error')}"

if mcp_server is not None:
    mcp_server.tool()(read_file)


async def list_files(path: str = ".") -> str:
    """Lists files under a directory."""
    tool = tool_registry.get_tool("list_files")
    if not tool:
        return "Error: Native list_files tool not registered."
    res = await tool.execute(path=path)
    if res.get("success"):
        return str(res["result"])
    return f"Error: {res.get('error')}"

if mcp_server is not None:
    mcp_server.tool()(list_files)


async def web_search(query: str) -> str:
    """Runs a web search using the configured search provider."""
    tool = tool_registry.get_tool("web_search")
    if not tool:
        return "Error: Native web_search tool not registered."
    res = await tool.execute(query=query)
    if res.get("success"):
        return str(res["result"])
    return f"Error: {res.get('error')}"

if mcp_server is not None:
    mcp_server.tool()(web_search)


# Define Prompts

def align_with_goals(instruction: str) -> str:
    """Create a prompt formatted to align the instruction with current active goals."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM goals WHERE status = 'pending' OR status = 'active'")
    goals = [r["title"] for r in cursor.fetchall()]
    conn.close()

    goals_summary = "\n".join([f"- {g}" for g in goals]) if goals else "- No specific goals configured."

    return (
        f"You are a strategic AI agent aligned with these specific goals:\n"
        f"{goals_summary}\n\n"
        f"Instruction to process:\n"
        f"{instruction}\n\n"
        f"Please perform the task in alignment with the goals above."
    )

if mcp_server is not None:
    mcp_server.prompt()(align_with_goals)


# FastAPI mount helper
def create_sse_app(mcp: Any = mcp_server) -> Starlette:
    """Create a Starlette app that handles SSE connections and message handling"""
    if not mcp_available or mcp is None:
        raise RuntimeError("Model Context Protocol is unavailable (mcp package is not installed).")
    transport = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            # Connect the streamable channel to the underlying FastMCP server session runner
            await mcp._mcp_server.run(
                streams[0], streams[1], mcp._mcp_server.create_initialization_options()
            )

    routes = [
        Route("/sse/", endpoint=handle_sse),
        Mount("/messages/", app=transport.handle_post_message),
    ]

    return Starlette(routes=routes)
