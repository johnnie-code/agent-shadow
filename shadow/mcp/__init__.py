# shadow.mcp — Model Context Protocol Proxy
try:
    from shadow.core.mcp_manager import mcp_manager
except ImportError:
    mcp_manager = None

try:
    from shadow.core.mcp_server import mcp_server
except ImportError:
    mcp_server = None
