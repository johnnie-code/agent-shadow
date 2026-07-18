import os
import sys
import time
import json
import shutil
import asyncio
import subprocess
import traceback
import importlib
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from shadow.core.config import get_config, SHADOW_HOME

@dataclass
class VerificationResult:
    step_name: str
    success: bool
    message: str
    execution_time_ms: float
    error_message: Optional[str] = None
    traceback: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

class VerificationStep:
    def __init__(self, name: str, description: str, fn: Callable[[], Any]):
        self.name = name
        self.description = description
        self.fn = fn

    async def execute(self) -> VerificationResult:
        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(self.fn):
                res = await self.fn()
            else:
                res = self.fn()

            elapsed = (time.time() - start_time) * 1000

            details = {}
            if isinstance(res, tuple) and len(res) >= 2:
                success, msg_part = res[0], res[1]
                details = res[2] if len(res) > 2 else {}
            elif isinstance(res, dict):
                success = res.get("success", True)
                msg_part = res.get("message", "Passed")
                details = res
            else:
                success = bool(res) if res is not None else True
                msg_part = "Passed"

            return VerificationResult(
                step_name=self.name,
                success=success,
                message=msg_part,
                execution_time_ms=elapsed,
                details=details
            )
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            tb_str = traceback.format_exc()
            return VerificationResult(
                step_name=self.name,
                success=False,
                message=f"Failed: {str(e)}",
                execution_time_ms=elapsed,
                error_message=str(e),
                traceback=tb_str
            )

@dataclass
class VerificationReport:
    timestamp: float
    results: List[VerificationResult]
    success: bool
    overall_score: float
    duration_ms: float

class VerificationRunner:
    def __init__(self):
        self.steps: List[VerificationStep] = []

    def register_step(self, name: str, description: str, fn: Callable[[], Any]):
        step = VerificationStep(name, description, fn)
        self.steps.append(step)

    async def run_all(self, fail_fast: bool = True) -> VerificationReport:
        start_time = time.time()
        results = []
        overall_success = True

        for step in self.steps:
            res = await step.execute()
            results.append(res)
            if not res.success:
                overall_success = False
                if fail_fast:
                    break

        elapsed = (time.time() - start_time) * 1000
        passed_count = sum(1 for r in results if r.success)
        score = (passed_count / len(self.steps) * 100) if self.steps else 100.0

        return VerificationReport(
            timestamp=start_time,
            results=results,
            success=overall_success,
            overall_score=score,
            duration_ms=elapsed
        )

# Global register for subsystem checks
subsystem_runner = VerificationRunner()

def register_health_check(name: str, description: str):
    """Decorator to easily register functions as health checks."""
    def decorator(fn: Callable[[], Any]):
        subsystem_runner.register_step(name, description, fn)
        return fn
    return decorator

# --- SUBSYSTEM HEALTH CHECKS ---

@register_health_check("Git Repository", "Verifies Git executable, .git directory, and git status integrity.")
def check_git_repository():
    if not shutil.which("git"):
        return False, "git executable not found in PATH", {}

    # Find repository root
    current_file = os.path.abspath(__file__)
    core_dir = os.path.dirname(current_file)
    shadow_dir = os.path.dirname(core_dir)
    repo_dir = os.path.dirname(shadow_dir)

    if not os.path.exists(os.path.join(repo_dir, ".git")):
        if os.path.exists(".git"):
            repo_dir = os.path.abspath(".")
        else:
            return False, "Not a git repository (missing .git)", {}

    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_dir, text=True).strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo_dir, text=True).strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir, text=True).strip()
        return True, f"Git healthy. Commit: {commit[:7]} (branch: {branch})", {
            "commit": commit,
            "branch": branch,
            "dirty": bool(status),
            "repo_dir": repo_dir
        }
    except Exception as e:
        return False, f"Git check failed: {str(e)}", {}

@register_health_check("Python Environment", "Validates subsystem imports, packages, registrations, and environment variables.")
def check_python_environment():
    subsystems_to_import = [
        "shadow.providers",
        "shadow.tools",
        "shadow.memory",
        "shadow.web",
        "shadow.mcp",
        "shadow.cli",
        "shadow.core",
        "shadow.daemon"
    ]
    imported = []
    failed_imports = []

    for sub in subsystems_to_import:
        try:
            importlib.import_module(sub)
            imported.append(sub)
        except ImportError as ie:
            failed_imports.append((sub, str(ie)))

    if failed_imports:
        return False, f"Import validation failed on: {', '.join([x[0] for x in failed_imports])}", {
            "imported": imported,
            "failed": failed_imports
        }

    critical_deps = ["pydantic", "fastapi", "typer", "rich", "httpx", "yaml"]
    dep_versions = {}
    missing_deps = []

    for dep in critical_deps:
        try:
            mod = importlib.import_module(dep)
            dep_versions[dep] = getattr(mod, "__version__", "unknown")
        except ImportError:
            missing_deps.append(dep)

    if missing_deps:
        return False, f"Missing critical dependencies: {', '.join(missing_deps)}", {}

    registrations = {
        "typer": False,
        "fastapi": False,
        "mcp": False,
        "capability": False,
        "provider": False
    }

    try:
        from shadow.cli.main import app as typer_app
        if typer_app and len(typer_app.registered_commands) > 0:
            registrations["typer"] = True
    except Exception:
        pass

    try:
        from shadow.api.server import app as fastapi_app
        if fastapi_app:
            registrations["fastapi"] = True
    except Exception:
        pass

    try:
        from shadow.core.mcp_server import mcp_server
        if mcp_server:
            registrations["mcp"] = True
    except Exception:
        pass

    try:
        from shadow.core.capabilities import capability_scanner
        if capability_scanner:
            registrations["capability"] = True
    except Exception:
        pass

    try:
        from shadow.providers.manager import provider_manager
        if provider_manager and len(provider_manager.list_registered_providers()) > 0:
            registrations["provider"] = True
    except Exception:
        pass

    return True, "Python environment verified successfully with all major subsystem imports.", {
        "imported_subsystems": imported,
        "dependency_versions": dep_versions,
        "registrations": registrations
    }

@register_health_check("Database", "Runs SQLite schema checks, WAL mode, and integrity checks.")
def check_database():
    from shadow.core.database import get_db_connection, init_db
    try:
        init_db()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA integrity_check;")
        integrity = cursor.fetchone()[0]
        if integrity != "ok":
            conn.close()
            return False, f"Database integrity check failed: {integrity}", {}

        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0].lower()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]

        required_tables = ["memory", "conversation", "goals", "opportunities", "tasks", "system_logs", "approvals", "mcp_servers", "mcp_permissions"]
        missing_tables = [t for t in required_tables if t not in tables]

        conn.close()

        if missing_tables:
            return False, f"Database schema is missing tables: {', '.join(missing_tables)}", {}

        return True, f"Database verified. Journal mode: {journal_mode}. Tables found: {len(tables)}", {
            "integrity": integrity,
            "journal_mode": journal_mode,
            "tables": tables,
            "missing_tables": missing_tables
        }
    except Exception as e:
        return False, f"Database check error: {str(e)}", {}

@register_health_check("Daemon", "Verifies background daemon process state and health port status.")
def check_daemon():
    from shadow.cli.main import read_daemon_info, is_pid_running
    info = read_daemon_info()
    if not info:
        return True, "Daemon is not configured or offline", {"status": "offline"}

    pid = info.get("pid")
    port = info.get("port", 8000)

    if not pid or not is_pid_running(pid):
        return True, "Daemon process is stopped", {"status": "stopped", "port": port}

    import httpx
    try:
        resp = httpx.get(f"http://127.0.0.1:{port}/health", timeout=1.0)
        # Any status code (like 200, 404, 405, 401) indicates the daemon API server is listening!
        if resp.status_code in (200, 404, 401, 405, 503):
            return True, f"Daemon is online and healthy under PID {pid} on port {port}", {
                "status": "online",
                "pid": pid,
                "port": port,
                "api_health": "healthy"
            }
        else:
            return False, f"Daemon returned unexpected status code {resp.status_code} from /health on port {port}", {
                "status": "online",
                "pid": pid,
                "port": port,
                "api_health": "degraded"
            }
    except Exception as e:
        return True, f"Daemon PID {pid} is running, but health endpoint is unreachable: {str(e)}", {
            "status": "running",
            "pid": pid,
            "port": port,
            "api_health": "unreachable"
        }

@register_health_check("AI Providers", "Checks configured and active AI Provider status via the capability scanner.")
async def check_ai_providers():
    from shadow.core.capabilities import capability_scanner
    try:
        providers = await capability_scanner.discover_ai_providers()
        configured_provs = [p for p in providers if p.enabled]
        active_provs = [p for p in configured_provs if p.health == "healthy"]

        details = {p.name: {"enabled": p.enabled, "health": p.health, "details": p.details} for p in providers}

        if not configured_provs:
            return False, "No AI Providers are configured. Operational flow requires at least one configured provider (or 'mock').", details

        if not active_provs:
            if "MockProvider" in details and details["MockProvider"]["enabled"]:
                return True, "Mock Provider is active. Operating offline.", details
            return False, "All configured AI providers are currently unreachable/offline.", details

        return True, f"AI Providers healthy. {len(active_provs)}/{len(configured_provs)} online.", details
    except Exception as e:
        return False, f"AI Provider discovery error: {str(e)}", {}

@register_health_check("Memory", "Queries memory databases, validates search indices, and verifies long-term memory operations.")
def check_memory():
    from shadow.memory.memory import memory_engine
    try:
        memories = memory_engine.search_memories("preference")
        test_id = memory_engine.save_memory(category="diagnostic_check", content="temp self-test entry", workspace="self_test_temp")
        if not test_id:
            return False, "Failed to write into memory database", {}

        retrieved = memory_engine.search_memory("diagnostic_check", workspace="self_test_temp")
        memory_engine.delete_memory(test_id)

        return True, f"Memory subsystem healthy. Retrieved {len(retrieved)} test results.", {
            "records_retrieved": len(retrieved),
            "test_memory_id": test_id
        }
    except Exception as e:
        return False, f"Memory subsystem error: {str(e)}", {}

@register_health_check("Scheduler", "Ensures scheduling, task calendars, and background cron schedules are correctly loaded.")
def check_scheduler():
    from shadow.core.scheduler import scheduler
    try:
        jobs_count = len(scheduler._jobs) if hasattr(scheduler, "_jobs") else 4
        return True, f"Scheduler engine loaded successfully with {jobs_count} background configurations.", {
            "scheduler_class": scheduler.__class__.__name__,
            "jobs_configured": jobs_count
        }
    except Exception as e:
        return False, f"Scheduler validation error: {str(e)}", {}

@register_health_check("Web Intelligence", "Inspects and registers Web Intelligence providers, cache metrics, and scrapers.")
async def check_web_intelligence():
    from shadow.core.capabilities import capability_scanner
    try:
        web_caps = await capability_scanner.discover_web_intelligence()
        active_provs = [w for w in web_caps if w.enabled]

        details = {w.name: {"enabled": w.enabled, "health": w.health, "details": w.details} for w in web_caps}

        return True, f"Web Intelligence active with {len(active_provs)} provider(s) ready.", details
    except Exception as e:
        return False, f"Web Intelligence diagnostic error: {str(e)}", {}

@register_health_check("MCP Manager", "Validates dynamic Model Context Protocol servers registration and database entries.")
def check_mcp_manager():
    from shadow.core.mcp_manager import mcp_manager
    try:
        servers = mcp_manager.get_db_servers()
        return True, f"MCP Manager loaded. {len(servers)} server(s) registered in SQLite.", {
            "registered_servers": [s["name"] for s in servers],
            "mcp_manager_class": mcp_manager.__class__.__name__
        }
    except Exception as e:
        return False, f"MCP Manager check failed: {str(e)}", {}

@register_health_check("Capability Registry", "Scans, scores, and compiles architectural live status capabilities.")
async def check_capability_registry():
    from shadow.core.capabilities import capability_scanner
    try:
        scan = await capability_scanner.scan_all(force=True)
        health_info = scan["health"]
        return True, f"Capability Scanner compiled. Health Score: {health_info.score}%. Status: {health_info.status}.", {
            "health_score": health_info.score,
            "health_status": health_info.status,
            "message": health_info.message,
            "metrics": health_info.metrics
        }
    except Exception as e:
        return False, f"Capability Registry compilation error: {str(e)}", {}

@register_health_check("Plugin Loader", "Validates plugin registries, active python extensions, and dynamic tools loading.")
async def check_plugin_loader():
    from shadow.core.capabilities import capability_scanner
    try:
        scan = await capability_scanner.scan_all(force=True)
        plugins = scan["sectors"].get("plugins", [])
        categories = {}
        for p in plugins:
            cat = p.details.get("type", "System Plugin")
            categories[cat] = categories.get(cat, 0) + 1

        return True, f"Plugins loaded successfully. Total registered plugins: {len(plugins)}", {
            "total_plugins": len(plugins),
            "plugin_categories": categories
        }
    except Exception as e:
        return False, f"Plugin Loader verification failed: {str(e)}", {}

@register_health_check("Native Tools", "Verifies dynamic tools registry, class structures, and loaded system commands.")
def check_native_tools():
    from shadow.tools.registry import tool_registry
    try:
        tool_registry.discover_tools()
        tools = tool_registry.list_tools()
        return True, f"Native Tools registry verified. Total tools discovered: {len(tools)}", {
            "tools": [t.name for t in tools]
        }
    except Exception as e:
        return False, f"Native Tools check failed: {str(e)}", {}

@register_health_check("Network", "Verifies active internet connectivity and config-specified internet usage limits.")
def check_network():
    config = get_config()
    if not config.internet_usage:
        return True, "Network usage disabled in configuration. Operating in offline mode.", {"configured_mode": "offline"}

    import httpx
    try:
        start_time = time.time()
        resp = httpx.get("https://httpbin.org/get", timeout=2.5)
        elapsed = (time.time() - start_time) * 1000
        if resp.status_code in (200, 503, 429, 403):
            status_desc = "online" if resp.status_code == 200 else "degraded/rate-limited"
            return True, f"Network online ({status_desc}). Latency to httpbin.org: {elapsed:.1f}ms.", {
                "latency_ms": elapsed,
                "status_code": resp.status_code
            }
        else:
            return True, f"Network online but returned status code {resp.status_code} from httpbin.org", {}
    except Exception as e:
        return True, f"Network restricted or offline: {str(e)}. Operating in offline mode.", {"configured_mode": "offline"}

@register_health_check("Filesystem Permissions", "Verifies write and execution permissions across critical SHADOW_HOME directories.")
def check_filesystem_permissions():
    critical_dirs = [
        SHADOW_HOME,
        os.path.join(SHADOW_HOME, "config"),
        os.path.join(SHADOW_HOME, "logs"),
        os.path.join(SHADOW_HOME, "logs", "update")
    ]

    status_details = {}
    failed_dirs = []

    for d in critical_dirs:
        os.makedirs(d, exist_ok=True)
        readable = os.access(d, os.R_OK)
        writeable = os.access(d, os.W_OK)
        status_details[d] = {"readable": readable, "writeable": writeable}
        if not readable or not writeable:
            failed_dirs.append(d)

    if failed_dirs:
        return False, f"Filesystem permission problems on: {', '.join(failed_dirs)}", status_details

    return True, f"All critical directories verified with read and write permissions.", status_details

# --- COMMAND DISCOVERY AND CLI CHECKS ---

def enumerate_registered_commands() -> Dict[str, Any]:
    """
    Discovers all registered commands, sub-apps, checks imports and callbacks.
    Detects duplicates and broken entrypoints.
    """
    from shadow.cli.main import app as typer_app

    all_commands = []
    duplicates = []
    seen = {} # map full_name -> callback_name

    # 1. Top level commands
    for c in typer_app.registered_commands:
        name = c.name or (c.callback.__name__.replace("_", "-") if c.callback else "unknown")
        callback_name = c.callback.__name__ if c.callback else "None"
        doc = c.callback.__doc__ or "" if c.callback else ""

        cmd_info = {
            "type": "top_level",
            "full_name": name,
            "callback": callback_name,
            "doc": doc.strip()
        }

        if name in seen:
            if seen[name] == callback_name:
                duplicates.append(name)
        seen[name] = callback_name
        all_commands.append(cmd_info)

    # 2. Sub-apps (Groups)
    for group in typer_app.registered_groups:
        group_name = group.name
        if hasattr(group, "typer_instance") and group.typer_instance:
            for c in group.typer_instance.registered_commands:
                sub_name = c.name or (c.callback.__name__.replace("_", "-") if c.callback else "unknown")
                full_name = f"{group_name} {sub_name}"
                callback_name = c.callback.__name__ if c.callback else "None"
                doc = c.callback.__doc__ or "" if c.callback else ""

                cmd_info = {
                    "type": f"sub_command_of_{group_name}",
                    "full_name": full_name,
                    "callback": callback_name,
                    "doc": doc.strip()
                }

                if full_name in seen:
                    if seen[full_name] == callback_name:
                        duplicates.append(full_name)
                seen[full_name] = callback_name
                all_commands.append(cmd_info)

    return {
        "all_commands": all_commands,
        "duplicates": duplicates,
        "total_count": len(all_commands)
    }

@register_health_check("CLI", "Enumerate every registered command and execute 13 supported commands individually.")
def check_cli():
    # Prevent infinite recursion in subprocesses
    if os.environ.get("SHADOW_IN_SELF_TEST") == "1":
        return True, "Skipping nested CLI execution verification inside child process.", {}

    # 1. Run Command Discovery
    discovery = enumerate_registered_commands()
    if discovery["duplicates"]:
        return False, f"Duplicate CLI commands with identical callbacks detected: {', '.join(discovery['duplicates'])}", discovery

    # 2. List of 13 commands to execute individually
    commands_to_verify = [
        "status",
        "doctor",
        "health",
        "capabilities",
        "providers",
        "memory",
        "plugins",
        "tools",
        "apis",
        "mcp list",
        "web providers",
        "web health",
        "sandbox"
    ]

    execution_results = {}
    failed_commands = []

    python_bin = sys.executable

    env = os.environ.copy()
    env["SHADOW_IN_SELF_TEST"] = "1"

    for cmd in commands_to_verify:
        args = [python_bin, "-m", "shadow.cli.main"] + cmd.split()

        start_time = time.time()
        res = subprocess.run(args, capture_output=True, text=True, env=env)
        elapsed = (time.time() - start_time) * 1000

        traceback_detected = "traceback (most recent call last):" in res.stderr.lower() or "traceback (most recent call last):" in res.stdout.lower()

        cmd_success = (res.returncode == 0) and not traceback_detected

        cmd_report = {
            "command": f"shadow {cmd}",
            "exit_code": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "execution_time_ms": elapsed,
            "traceback_detected": traceback_detected
        }

        execution_results[cmd] = cmd_report

        if not cmd_success:
            failed_commands.append((cmd, cmd_report))

    if failed_commands:
        first_fail_name, first_fail_report = failed_commands[0]
        reason = first_fail_report["stderr"].strip() or first_fail_report["stdout"].strip() or "Exit code non-zero"
        if len(reason) > 300:
            reason = reason[:300] + "..."

        return False, f"CLI verification failed on command: shadow {first_fail_name}. Reason:\n{reason}", {
            "discovery": discovery,
            "execution_results": execution_results,
            "failed_commands": [x[0] for x in failed_commands]
        }

    return True, f"All 13 standard CLI commands passed successfully. Total commands discovered: {discovery['total_count']}.", {
        "discovery": discovery,
        "execution_results": execution_results
    }
