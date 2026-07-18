# Project Shadow: System Architecture

Shadow is a modular, autonomous, goal-driven agent operating system designed to run entirely on Android via Termux or in any standard Python environment.

With Phase 2A, Shadow evolved from a hardcoded single-provider assistant into an **MCP-native Autonomous Platform** utilizing provider abstraction, capability registries, and a unified tool execution core.

## Target Architecture Layout

```
                                  Ghost (Orchestrator)
                                           │
                ┌──────────────────────────┼──────────────────────────┐
                │                          │                          │
        ProviderManager               Tool Engine                Memory Engine
                │                          │                          │
         ┌──────┴──────┐                   │                  ┌───────┴───────┐
         │             │                   │                  │               │
      Ollama        Gemini                 │              Long-term       Workspace
      Claude        OpenAI                 │               Memory          Memory
      Local LLMs    Future                 │
                                           │
                           ┌───────────────┴────────────────┐
                           │                                │
                     Native Tools                      MCP Manager
                           │                                │
                      Filesystem                       GitHub MCP
                      Git                              Notion MCP
                      Shell                            Playwright MCP
                      Browser                          Firecrawl MCP
                      Sandbox                          Supabase MCP
                      Android                          SQLite MCP
                      Debugger                         PostgreSQL MCP
                      Research                         Docker MCP
```

---

## Architecture Subsystems

### 1. Provider Abstraction Layer (`ProviderManager`)
The `ProviderManager` is the single point of entry for all AI models in Shadow. Ghost (the agents and planning engine) never communicates directly with a specific provider, but instead communicates solely with the `ProviderManager`.

- **Standard Interface**: Every provider implements the `BaseProvider` class (`shadow/providers/base.py`) which defines standard lifecycle and utility hooks:
  - `initialize()` / `shutdown()`
  - `health_check()` -> returns `async bool`
  - `chat(messages)` / `stream_chat(messages)` -> returns response payload, estimated cost, and token count.
  - `complete(prompt)` / `embed(texts)`
  - Feature capability flags: `supports_tools()`, `supports_streaming()`, `supports_images()`, `supports_reasoning()`, `supports_embeddings()`, `supports_mcp()`.
- **Dynamic Routing**: Routes queries to the best provider based on the task description (e.g., coding -> Claude; analysis -> Gemini; conversation -> Ollama).
- **Automated Fallbacks**: Automatically cycles through fallback channels (Ollama Cloud -> Ollama Local -> Gemini -> Mock) if an active provider fails, preventing any system hangs.

### 2. Model Context Protocol (`MCPManager`)
Shadow acts as both an **MCP Client** and an **MCP Server**.

- **MCP Client (Stdio & SSE Transports)**: Connects to external servers via standard processes (`stdio`) or HTTP streams (`SSE`). Support is built in for custom headers, OAuth, API Keys, and workspace overrides.
- **Server Registry & Management**: Stores server status (`running`, `stopped`, `disabled`), connection parameters, and assignment settings.
- **Automated Discovery**: Dynamically queries the capabilities of connected servers and registers their tools, resources, and prompts in SQLite.
- **Permission System**: Every MCP tool has user-configurable safety boundaries:
  - **Always Allow**: Auto-execution without verification.
  - **Allow Once**: Executes and then resets to confirmation.
  - **Ask Every Time**: Pauses and requests manual approval via CLI.
  - **Deny**: Fails instantly without hitting the server.
- **MCP Server Capabilities**: Exposes Shadow's own goal registries, opportunities list, and persistent memories as read-only resources, alongside native tool registries via stdio/SSE.

### 3. Unified Tool Engine
Exposes native tools and dynamic MCP tools through the exact same execution pipeline.

- **MCP Tool Adapter**: Wraps dynamic MCP tools inside a standard `Tool` signature, enabling them to be executed identically to native tools with timeout and cancellation guarantees.
- **Autonomous Tool Resolution**: Inspects task descriptions and automatically assigns them to MCP tools when appropriate (e.g. updating Notion roadmaps or searching docs).

### 4. Event Bus & Observability
- **Event Bus (`shadow/core/events.py`)**: Non-coupling publish/subscribe channel for lifecycle and operational signals (`ProviderConnected`, `ProviderFailed`, `MCPConnected`, `ToolExecuted`, `MemoryUpdated`).
- **Observability**: Records request latency, token consumption, and cost estimates in standard WAL log tables.

---

## Extension Points

### How to Add a New AI Provider
1. Create a class inheriting from `BaseProvider` in `shadow/providers/`.
2. Implement required abstract methods (`chat`, `calculate_cost`).
3. Register the new provider class with `provider_manager.register_provider(name, instance)` in `shadow/providers/manager.py`.

### How to Add a New MCP Server
Register the server through the CLI or python programmatic script:
```bash
shadow mcp install <server_name> --transport stdio --cmd "uvx" --args "mcp-server-git"
```

### How to Add a New Native Tool
Create a class inheriting from `Tool` under `shadow/tools/` (e.g. `shadow/tools/my_tool.py`). The dynamic scanner will automatically discover and register the tool upon system startup.
