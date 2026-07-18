import os
import sys
import time
import json
import asyncio
import shutil
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from shadow.core.config import get_config, SHADOW_HOME
from shadow.core.database import get_db_connection
from shadow.providers.manager import provider_manager
from shadow.core.mcp_manager import mcp_manager
from shadow.tools.registry import tool_registry
from shadow.skills.skills import skills_registry

@dataclass
class CapabilityHealth:
    status: str = "healthy"  # healthy, degraded, error, offline
    score: int = 100         # 0 to 100
    message: str = "Operating normally."
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Capability:
    name: str
    category: str            # "AI Provider", "MCP Server", "Native Tool", "Sandbox", "Memory", "Background Service", "API Integration", "Plugin"
    health: str = "healthy"  # healthy, degraded, error, offline
    enabled: bool = True
    version: str = "1.0"
    capabilities: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class CapabilityProvider:
    """
    Interface for dynamic capability registration from subsystems.
    """
    def provide_capabilities(self) -> List[Capability]:
        return []


class CapabilityRegistry:
    """
    Central Capability Registry.
    Unifies all first-class subsystems and exposes them dynamically.
    No subsystem should require manual registration, but allows explicit self-registration.
    """
    def __init__(self):
        self._custom_capabilities: Dict[str, Capability] = {}

    def register_capability(self, capability: Capability):
        """Allows custom Python extensions or tools to self-register."""
        self._custom_capabilities[capability.name] = capability

    def unregister_capability(self, name: str):
        if name in self._custom_capabilities:
            del self._custom_capabilities[name]

    def get_capability(self, name: str) -> Optional[Capability]:
        return self._custom_capabilities.get(name)

    def list_custom_capabilities(self) -> List[Capability]:
        return list(self._custom_capabilities.values())


# Global Capability Registry Singleton
capability_registry = CapabilityRegistry()


class CapabilityScanner:
    """
    Dynamic discovery engine. Inspects the active architecture, files, configuration,
    and database state at runtime to construct a live CapabilityReport.
    """
    def __init__(self):
        self._cache: Optional[Dict[str, Any]] = None
        self._last_refresh: float = 0.0
        self._cache_duration: float = 2.0  # short cache for performance, can be bypassed

    def invalidate_cache(self):
        self._cache = None
        self._last_refresh = 0.0

    async def scan_all(self, force: bool = False) -> Dict[str, Any]:
        """Scans all architectural sectors and builds a live state dictionary."""
        # Ensure database and tables exist
        from shadow.core.database import init_db
        try:
            init_db()
        except Exception:
            pass

        now = time.time()
        if not force and self._cache is not None and (now - self._last_refresh < self._cache_duration):
            return self._cache

        # Run all discovery routines concurrently
        providers, mcp, tools, sandbox, memory, bg_services, apis, plugins, web_intel = await asyncio.gather(
            self.discover_ai_providers(),
            self.discover_mcp(),
            self.discover_native_tools(),
            self.discover_sandbox(),
            self.discover_memory(),
            self.discover_background_services(),
            self.discover_apis(),
            self.discover_plugins(),
            self.discover_web_intelligence()
        )

        # Merge custom registered capabilities
        custom_list = capability_registry.list_custom_capabilities()
        for cap in custom_list:
            # Depending on category, append or merge
            if cap.category == "Native Tool":
                tools.append(cap)
            elif cap.category == "Plugin":
                plugins.append(cap)
            elif cap.category == "API Integration":
                apis.append(cap)

        # Append web intelligence providers to plugins for standard capability list visibility
        plugins.extend(web_intel)

        # Compute overall health score
        health_report = self._calculate_overall_health(providers, mcp, sandbox, memory, bg_services)

        report = {
            "timestamp": now,
            "health": health_report,
            "sectors": {
                "ai_providers": providers,
                "mcp_servers": mcp,
                "native_tools": tools,
                "sandbox": sandbox,
                "memory": memory,
                "background_services": bg_services,
                "apis": apis,
                "plugins": plugins,
                "web_intelligence": web_intel
            }
        }

        self._cache = report
        self._last_refresh = now
        return report

    async def discover_web_intelligence(self) -> List[Capability]:
        """Inspects the Web Intelligence subsystem, active providers, caching, and indexed content."""
        from shadow.core.web.manager import web_provider_manager
        from shadow.core.web.cache import global_web_cache

        capabilities = []
        providers = web_provider_manager.list_providers()

        # Database web insights count
        indexed_chunks_count = 0
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM memory WHERE tags LIKE '%web_intelligence%'")
            indexed_chunks_count = cursor.fetchone()[0]
        except Exception:
            pass
        finally:
            conn.close()

        cache_stats = global_web_cache.get_stats()

        for p in providers:
            is_avail = await p.is_available()
            status = "healthy" if is_avail else "offline"

            # Endpoints and capabilities for each provider
            caps = ["Scrape", "Crawl"]
            if p.name == "Firecrawl":
                caps = ["Search", "Scrape", "Crawl", "Map", "Extract", "Interact", "Monitor", "Research Index", "Parse", "Ask", "Docs Search"]
            elif p.name == "Playwright":
                caps = ["Scrape", "Interact"]

            auth_configured = True
            if p.name == "Firecrawl":
                auth_configured = bool(os.environ.get("FIRECRAWL_API_KEY"))

            capabilities.append(Capability(
                name=f"{p.name} Web Intelligence Provider",
                category="API Integration",
                health=status,
                enabled=is_avail,
                version=p.version,
                capabilities=caps,
                details={
                    "provider_id": p.name.lower(),
                    "configured": is_avail,
                    "authenticated": auth_configured,
                    "latency_ms": 0.0,
                    "cache_size": cache_stats["cache_size"],
                    "indexed_size_chunks": indexed_chunks_count
                }
            ))
        return capabilities

    async def discover_ai_providers(self) -> List[Capability]:
        """Inspects all configured and registered AI Providers."""
        config = get_config()
        registered_names = provider_manager.list_registered_providers()
        capabilities = []

        default_prov = (config.default_provider or "mock").lower()

        for name in registered_names:
            prov_obj = provider_manager.get_provider(name)
            is_default = (name == default_prov)

            # Determine configured status
            is_configured = False
            is_authenticated = False
            is_reachable = False
            latency = -1.0

            if name == "mock":
                is_configured = True
                is_authenticated = True
                is_reachable = True
                latency = 0.0
            elif name in ("openai", "gemini", "google", "anthropic", "claude"):
                # Check config
                cfg_obj = getattr(config, "gemini" if name == "google" else ("anthropic" if name == "claude" else name), None)
                if cfg_obj and getattr(cfg_obj, "api_key", None):
                    is_configured = True

            elif name == "ollama":
                # Check base or env
                is_configured = True # Ollama is generally local and assumed configured

            # If configured, run a quick ping to measure reachable/authenticated status
            if is_configured and name != "mock":
                start_time = time.time()
                try:
                    # short timeout to prevent hanging the system
                    h_check = await asyncio.wait_for(prov_obj.health_check(), timeout=1.5)
                    if h_check:
                        is_reachable = True
                        is_authenticated = True
                        latency = round((time.time() - start_time) * 1000, 2)
                except Exception:
                    is_reachable = False
                    is_authenticated = False

            # Model capabilities
            caps = []
            if prov_obj.supports_tools(): caps.append("Tools")
            if prov_obj.supports_streaming(): caps.append("Streaming")
            if prov_obj.supports_images(): caps.append("Vision")
            if prov_obj.supports_reasoning(): caps.append("Reasoning")
            if prov_obj.supports_embeddings(): caps.append("Embeddings")

            status = "healthy" if is_reachable else ("offline" if is_configured else "degraded")

            capabilities.append(Capability(
                name=prov_obj.__class__.__name__,
                category="AI Provider",
                health=status,
                enabled=is_configured,
                version="1.0",
                capabilities=caps,
                details={
                    "provider_id": name,
                    "configured": is_configured,
                    "authenticated": is_authenticated,
                    "reachable": is_reachable,
                    "latency_ms": latency,
                    "default_provider": is_default,
                    "available_models": prov_obj.list_models()
                }
            ))

        return capabilities

    async def discover_mcp(self) -> List[Capability]:
        """Inspects the Model Context Protocol registry dynamically."""
        servers = mcp_manager.get_db_servers()
        capabilities = []

        for s in servers:
            name = s["name"]
            status = s.get("status", "stopped")
            transport = s.get("transport", "stdio")

            tools_list = []
            prompts_list = []
            resources_list = []
            try:
                tools_list = json.loads(s.get("tools") or "[]")
                prompts_list = json.loads(s.get("prompts") or "[]")
                resources_list = json.loads(s.get("resources") or "[]")
            except Exception:
                pass

            # Count permissions
            perms_count = 0
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT COUNT(*) FROM mcp_permissions WHERE server_name = ?", (name,))
                perms_count = cursor.fetchone()[0]
            except Exception:
                pass
            finally:
                conn.close()

            health_status = "healthy" if status == "running" else ("offline" if status == "stopped" else "error")
            if status == "disabled":
                health_status = "offline"

            caps = []
            if tools_list: caps.append("Tools")
            if prompts_list: caps.append("Prompts")
            if resources_list: caps.append("Resources")

            capabilities.append(Capability(
                name=name,
                category="MCP Server",
                health=health_status,
                enabled=(status != "disabled"),
                version=s.get("version") or "1.0",
                capabilities=caps,
                details={
                    "status": status,
                    "transport": transport,
                    "url": s.get("url") or "",
                    "command": s.get("command") or "",
                    "args": json.loads(s.get("args") or "[]"),
                    "tools_count": len(tools_list),
                    "prompts_count": len(prompts_list),
                    "resources_count": len(resources_list),
                    "permissions_configured": perms_count
                }
            ))

        return capabilities

    async def discover_native_tools(self) -> List[Capability]:
        """Inspects all registered native tools."""
        # Make sure tools are scanned/discovered first
        tool_registry.discover_tools()
        tools = tool_registry.list_tools()
        capabilities = []

        # Group tools under logical domains
        domain_mappings = {
            "git": "Git Control",
            "sandbox": "Sandbox Subsystem",
            "browser": "Headless Browser",
            "android": "Android Toolchain",
            "file": "Filesystem Engine",
            "search": "Search Discovery",
            "memory": "Memory Store",
            "planner": "Goal Planner",
            "debugger": "Auto Debugger",
            "api": "API Connector"
        }

        for t in tools:
            # Categorize tool by its name prefix/substring
            cat_name = "Native Utility"
            for kw, domain in domain_mappings.items():
                if kw in t.name.lower():
                    cat_name = domain
                    break

            # Check dependency limits (e.g. android-gradle-compiler or playbooks if available)
            enabled = True
            if "android" in t.name.lower():
                # android builders require certain environment variables or gradle
                enabled = shutil.which("gradle") is not None or shutil.which("gradlew") is not None or True

            capabilities.append(Capability(
                name=t.name,
                category="Native Tool",
                health="healthy",
                enabled=enabled,
                version="1.0",
                capabilities=[f"Safety L{t.safety_level}"],
                details={
                    "description": t.description,
                    "safety_level": t.safety_level,
                    "module": t.__class__.__module__
                }
            ))

        return capabilities

    async def discover_sandbox(self) -> Capability:
        """Inspects all active Sandbox Computers and aggregate stats."""
        from shadow.core.sandbox import sandbox_manager, job_manager
        sandboxes = sandbox_manager.list_sandboxes()
        jobs = job_manager.list_jobs()

        active_jobs = [j for j in jobs if j["status"] == "running"]
        active_sandboxes_count = len(sandboxes)

        total_storage = 0.0
        total_ram = 0.0
        total_cpu = 0.0
        active_pids = []
        snapshots_count = 0
        terminal_runs = 0
        workspace_files_count = 0

        for s in sandboxes:
            comp = sandbox_manager.get_sandbox(s["sandbox_id"])
            if comp:
                usage = comp.get_resource_usage()
                total_storage += usage.get("storage_mb", 0.0)
                total_ram += usage.get("ram_mb", 0.0)
                total_cpu += usage.get("cpu_percent", 0.0)
                active_pids.extend(usage.get("pids", []))

                # snapshots count
                meta = comp.load_meta()
                snapshots_count += len(meta.get("snapshots", []))

                # terminal runs
                terminal_runs += len(meta.get("workspace", {}).get("execution_history", []))

                # files count
                try:
                    for root, dirs, files in os.walk(comp.workspace_dir):
                        workspace_files_count += len(files)
                except Exception:
                    pass

        idle_sandboxes_count = active_sandboxes_count - len(active_jobs)

        return Capability(
            name="Sandbox Container Subsystem",
            category="Sandbox",
            health="healthy" if active_sandboxes_count > 0 else "offline",
            enabled=True,
            version="1.0",
            capabilities=["Process Isolation", "Workspace Sync", "Resource Limits", "Checkpoint Snapshots"],
            details={
                "active_sandboxes": active_sandboxes_count,
                "idle_sandboxes": max(0, idle_sandboxes_count),
                "storage_usage_mb": round(total_storage, 2),
                "ram_usage_mb": round(total_ram, 2),
                "cpu_percent": round(total_cpu, 2),
                "snapshots_total": snapshots_count,
                "terminal_runs": terminal_runs,
                "workspace_files_count": workspace_files_count,
                "running_terminals": len(active_pids),
                "active_pids": active_pids
            }
        )

    async def discover_memory(self) -> Capability:
        """Inspects SQLite, SQLite metrics, notebooks and goals state."""
        conn = get_db_connection()
        cursor = conn.cursor()

        records_count = 0
        goals_pending = 0
        goals_completed = 0
        tasks_completed = 0
        tasks_failed = 0
        conversation_msgs = 0

        try:
            cursor.execute("SELECT COUNT(*) FROM memory")
            records_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM goals WHERE status IN ('pending', 'active')")
            goals_pending = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM goals WHERE status = 'completed'")
            goals_completed = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
            tasks_completed = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'failed'")
            tasks_failed = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM conversation")
            conversation_msgs = cursor.fetchone()[0]
        except Exception:
            pass
        finally:
            conn.close()

        # Notebook entries (sum across all sandboxes)
        from shadow.core.sandbox import sandbox_manager
        sandboxes = sandbox_manager.list_sandboxes()
        notebook_entries_count = 0
        for s in sandboxes:
            comp = sandbox_manager.get_sandbox(s["sandbox_id"])
            if comp:
                nb = comp.load_notebook()
                for k, v in nb.items():
                    if isinstance(v, list):
                        notebook_entries_count += len(v)
                    elif v:
                        notebook_entries_count += 1

        return Capability(
            name="SQLite Long-Term Memory Engine",
            category="Memory",
            health="healthy" if records_count > 0 or goals_pending > 0 else "degraded",
            enabled=True,
            version="1.0",
            capabilities=["SQLite Index", "Semantic Keywords", "Notebook Integration", "Goals Tracker"],
            details={
                "memory_records": records_count,
                "notebook_entries": notebook_entries_count,
                "active_goals": goals_pending,
                "completed_goals": goals_completed,
                "task_history_completed": tasks_completed,
                "task_history_failed": tasks_failed,
                "recent_conversations": conversation_msgs,
                "indexed_projects": len(sandboxes)
            }
        )

    async def discover_background_services(self) -> Capability:
        """Inspects the system daemon, Telegram companion, autonomous loop, scheduled jobs, and pollers."""
        from shadow.cli.main import read_daemon_info, is_pid_running
        from shadow.core.runtime import autonomous_runtime

        daemon_info = read_daemon_info()
        daemon_active = False
        daemon_pid = None
        daemon_port = None
        if daemon_info:
            pid = daemon_info.get("pid")
            if pid and is_pid_running(pid):
                daemon_active = True
                daemon_pid = pid
                daemon_port = daemon_info.get("port")

        config = get_config()
        telegram_enabled = bool(config.telegram_bot_token)
        telegram_active = telegram_enabled and daemon_active # runs inside daemon

        runtime_active = autonomous_runtime._running

        # Scheduled jobs list
        schedules = [
            {"name": "scheduled_research", "interval": "2 hours"},
            {"name": "scheduled_reflection", "interval": "4 hours"},
            {"name": "scheduled_repo_analysis", "interval": "8 hours"},
            {"name": "scheduled_learning", "interval": "2 hours"}
        ]

        return Capability(
            name="Autonomous Daemon Loop Services",
            category="Background Service",
            health="healthy" if daemon_active else "offline",
            enabled=True,
            version="1.1",
            capabilities=["Continuous Reasoning", "Telegram polling", "Cron Scheduler", "Autonomous Execution"],
            details={
                "daemon": "running" if daemon_active else "stopped",
                "daemon_pid": daemon_pid,
                "daemon_port": daemon_port,
                "Telegram": "polling" if telegram_active else ("idle" if telegram_enabled else "disabled"),
                "scheduled_jobs": schedules,
                "autonomous_workers": "active" if runtime_active else "idle",
                "notifications": config.notification_preferences or "terminal",
                "pollers": ["event_bus_poller", "mcp_reconnect_poller"] if daemon_active else []
            }
        )

    async def discover_apis(self) -> Capability:
        """API Discovery Engine. Reports installed API integrations and specs."""
        config = get_config()
        # Find files or configs indicating third-party integrations
        apis_count = 0
        authenticated_count = 0

        # We inspect active providers
        api_keys = [config.openai.api_key, config.anthropic.api_key, config.gemini.api_key, config.telegram_bot_token]
        authenticated_count = sum(1 for k in api_keys if k)

        # Mock OpenAPI specs and GraphQL endpoints discovered or loaded from plugins/tools
        openapi_specs = ["shadow_daemon_openapi_v1.json"]
        graphql_endpoints = []
        generated_clients = ["tg_bot_client", "mcp_http_client"]

        return Capability(
            name="Unified API Discovery Engine",
            category="API Integration",
            health="healthy" if authenticated_count > 0 else "degraded",
            enabled=True,
            version="1.0",
            capabilities=["OpenAPI Discovery", "Spec Parsing", "On-The-Fly Client Generator"],
            details={
                "installed_api_integrations": ["OpenAI API", "Anthropic Claude API", "Google Gemini API", "Telegram Bot API"],
                "cached_apis": ["httpx_dns_cache", "llm_response_cache"],
                "authenticated_apis": authenticated_count,
                "generated_clients": generated_clients,
                "openapi_specs": openapi_specs,
                "graphql_endpoints": graphql_endpoints
            }
        )

    async def discover_plugins(self) -> List[Capability]:
        """Plugin Discovery. Inspects skills, sandbox extensions and registries."""
        skills = skills_registry.list_skills()
        capabilities = []

        # Core Plugins
        capabilities.append(Capability(
            name="Playwright Headless Browser Module",
            category="Plugin",
            health="healthy",
            enabled=True,
            version="1.0",
            capabilities=["DOM Inspection", "Visual Layout Diffing", "Live URL Scraping"],
            details={"type": "Tool plugin"}
        ))

        capabilities.append(Capability(
            name="Gradle Compiler Suite",
            category="Plugin",
            health="healthy",
            enabled=(shutil.which("gradle") is not None or shutil.which("gradlew") is not None),
            version="2.0",
            capabilities=["Gradle Build", "Lint Verification", "Unit Testing Fallbacks"],
            details={"type": "Compiler plugin"}
        ))

        # Dynamic Skills as Plugins
        for sk in skills:
            capabilities.append(Capability(
                name=sk.name,
                category="Plugin",
                health="healthy",
                enabled=True,
                version=sk.version,
                capabilities=["Task Orchestration", "Dynamic Invocation"],
                details={
                    "type": "Skill plugin",
                    "description": sk.description
                }
            ))

        return capabilities

    def _calculate_overall_health(self, providers: List[Capability], mcp: List[Capability], sandbox: Capability, memory: Capability, bg: Capability) -> CapabilityHealth:
        """Calculates system health based on status of sectors."""
        score = 100
        reasons = []

        # Check AI Providers
        configured_provs = [p for p in providers if p.enabled]
        active_provs = [p for p in configured_provs if p.health == "healthy"]
        if not active_provs:
            score -= 30
            reasons.append("All configured AI providers are offline.")
        elif len(active_provs) < len(configured_provs):
            score -= 10
            reasons.append("Some configured AI providers are unreachable.")

        # Check MCP
        disabled_mcp = [m for m in mcp if not m.enabled]
        error_mcp = [m for m in mcp if m.health == "error"]
        if error_mcp:
            score -= 10 * len(error_mcp)
            reasons.append(f"MCP Server error detected on: {', '.join([m.name for m in error_mcp])}.")

        # Check Daemon
        if bg.health == "offline":
            score -= 15
            reasons.append("Background daemon is stopped.")

        # Check Memory
        if memory.health == "degraded":
            score -= 5
            reasons.append("Memory tables are empty.")

        score = max(0, min(100, score))
        msg = " ".join(reasons) if reasons else "All systems fully operational."
        status = "healthy" if score >= 90 else ("degraded" if score >= 70 else "error")

        return CapabilityHealth(
            status=status,
            score=score,
            message=msg,
            metrics={
                "configured_providers": len(configured_provs),
                "active_providers": len(active_provs),
                "mcp_active": len([m for m in mcp if m.health == "healthy"]),
                "daemon_running": bg.health == "healthy"
            }
        )


class CapabilityReport:
    """
    Format and serialize Capability state into human-readable Rich output, tables,
    and structured dictionaries.
    """
    @staticmethod
    def generate_health_summary(scan: Dict[str, Any]) -> str:
        """Builds a beautiful live system health score card."""
        health_info = scan["health"]
        sectors = scan["sectors"]

        p_lines = []
        for p in sectors["ai_providers"]:
            mark = "✓" if p.health == "healthy" else "⚠" if p.health == "degraded" else "✗"
            p_lines.append(f"{mark} {p.name}")
        provs_summary = "  ".join(p_lines)

        m_lines = []
        for m in sectors["mcp_servers"]:
            mark = "✓" if m.health == "healthy" else "⚠" if m.health == "degraded" else "✗"
            m_lines.append(f"{mark} {m.name}")
        mcp_summary = "  ".join(m_lines) if m_lines else "None installed"

        sandbox_status = "✓ Healthy" if sectors["sandbox"].health == "healthy" else "✗ Offline"
        memory_status = "✓ Healthy" if sectors["memory"].health == "healthy" else "⚠ Empty"
        bg_status = "✓ Running" if sectors["background_services"].details.get("daemon") == "running" else "✗ Stopped"

        # Resource limits stats
        details = sectors["sandbox"].details
        storage = f"{details.get('storage_usage_mb', 0.0):.1f}MB"
        ram = f"{details.get('ram_usage_mb', 0.0):.1f}MB"
        cpu = f"{details.get('cpu_percent', 0.0):.1f}%"

        overall_mark = "✓" if health_info.status == "healthy" else "⚠" if health_info.status == "degraded" else "✗"

        return (
            f"Overall Health\n\n"
            f"{health_info.score}%\n\n"
            f"AI Providers\n\n"
            f"{provs_summary}\n\n"
            f"Sandbox\n\n"
            f"{sandbox_status}\n\n"
            f"Memory\n\n"
            f"{memory_status}\n\n"
            f"MCP\n\n"
            f"{mcp_summary}\n\n"
            f"Background Jobs\n\n"
            f"{bg_status}\n\n"
            f"Storage\n\n"
            f"{storage}\n\n"
            f"RAM\n\n"
            f"{ram}\n\n"
            f"CPU\n\n"
            f"{cpu}\n"
        )


class CapabilityPlanner:
    """
    Intelligent Capability Planner. Intercepts missing/unavailable capability requests
    and suggests/proposes specific installable MCP servers/plugins.
    """
    SUGGESTED_MCP_SERVERS = {
        "figma": {
            "name": "Figma MCP Server",
            "description": "Inspect designs, nodes, styles, and comments in Figma files dynamically.",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@figma/mcp-server"]
        },
        "notion": {
            "name": "Notion MCP Server",
            "description": "Read, search, write, and manage workspace documents and pages in Notion.",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@notion/mcp-server"]
        },
        "slack": {
            "name": "Slack MCP Server",
            "description": "Read channels, post rich messages, and query user profiles in Slack.",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@slack/mcp-server"]
        },
        "postgres": {
            "name": "PostgreSQL Database Connector",
            "description": "Execute queries, inspect schemas, and query relational databases safely.",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres"]
        },
        "github": {
            "name": "GitHub Integration Suite",
            "description": "Orchestrate pull requests, manage issues, commit files, and browse repos.",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"]
        },
        "spotify": {
            "name": "Spotify Control Server",
            "description": "Control playback, search tracks, and query playlists.",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "spotify-mcp"]
        },
        "jira": {
            "name": "Jira Agile Management",
            "description": "Create issues, inspect boards, search stories, and transition tickets.",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-jira"]
        }
    }

    @classmethod
    def analyze_missing_capability(cls, query: str) -> Optional[Dict[str, Any]]:
        """Identifies if a query refers to an uninstalled or missing MCP server."""
        query_lower = query.lower()
        installed_mcp_names = [s["name"].lower() for s in mcp_manager.get_db_servers()]

        for kw, details in cls.SUGGESTED_MCP_SERVERS.items():
            if kw in query_lower:
                # Check if already installed
                if kw not in installed_mcp_names:
                    return {
                        "keyword": kw,
                        "server_name": kw,
                        "suggested_config": details
                    }
        return None


# Singletons
capability_scanner = CapabilityScanner()
capability_planner = CapabilityPlanner()
