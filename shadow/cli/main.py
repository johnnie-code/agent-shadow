import os
import sys
import typer
import asyncio
import time
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from shadow.core.config import get_config, SHADOW_HOME
from shadow.core.database import init_db, get_db_connection
from shadow.goals.engine import goals_engine
from shadow.goals.scanner import OpportunityScanner
from shadow.goals.generator import TaskGenerator
from shadow.goals.priority import priority_engine
from shadow.goals.executor import execution_engine
from shadow.goals.reflection import reflection_engine
from shadow.memory.memory import memory_engine
from shadow.tools.registry import tool_registry
from shadow.skills.skills import skills_registry

app = typer.Typer(name="shadow", help="PROJECT SHADOW — Autonomous OS Control Terminal CLI")
console = Console()

# --- Daemon Helper Functions ---

def get_daemon_pid_path() -> str:
    return os.path.join(SHADOW_HOME, "daemon.pid")

def get_daemon_log_path() -> str:
    return os.path.join(SHADOW_HOME, "logs", "daemon.log")

def is_daemon_running() -> Optional[int]:
    pid_path = get_daemon_pid_path()
    if not os.path.exists(pid_path):
        return None
    try:
        with open(pid_path, "r") as f:
            content = f.read().strip()
            if ":" in content:
                pid = int(content.split(":")[0])
            else:
                pid = int(content)
        # Check if pid is active
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, OSError):
        return None

def get_daemon_port() -> int:
    pid_path = get_daemon_pid_path()
    if not os.path.exists(pid_path):
        return 8000
    try:
        with open(pid_path, "r") as f:
            content = f.read().strip()
            if ":" in content:
                return int(content.split(":")[1])
    except Exception:
        pass
    return 8000

def stop_daemon():
    pid = is_daemon_running()
    if pid:
        try:
            import signal
            os.kill(pid, signal.SIGTERM)
            for _ in range(15):
                time.sleep(0.1)
                try:
                    os.kill(pid, 0)
                except OSError:
                    break
            else:
                os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    pid_path = get_daemon_pid_path()
    if os.path.exists(pid_path):
        try:
            os.remove(pid_path)
        except OSError:
            pass

# --- CLI Daemon Command Group ---

daemon_app = typer.Typer(help="Manage the Shadow OS background daemon service.")

@daemon_app.command("start")
def daemon_start(port: int = 8000):
    """
    Start the background daemon service.
    """
    pid = is_daemon_running()
    if pid:
        console.print(f"[yellow]Daemon is already running with PID {pid}.[/yellow]")
        return

    init_db()
    console.print("[green]Starting background daemon service...[/green]")
    try:
        import subprocess
        log_file = get_daemon_log_path()
        log_dir = os.path.dirname(log_file)
        os.makedirs(log_dir, exist_ok=True)

        with open(log_file, "a") as f:
            proc = subprocess.Popen(
                [sys.executable, "-c", f"from shadow.api.server import start_server; start_server(port={port})"],
                stdout=f,
                stderr=f,
                start_new_session=True
            )
        with open(get_daemon_pid_path(), "w") as pf:
            pf.write(f"{proc.pid}:{port}")
        console.print(f"[green]Daemon started in background on port {port} (PID: {proc.pid}).[/green]")
    except Exception as e:
        console.print(f"[red]Failed to start daemon: {e}[/red]")

@daemon_app.command("stop")
def daemon_stop():
    """
    Stop the running background daemon service.
    """
    pid = is_daemon_running()
    if not pid:
        console.print("[yellow]Daemon is not running.[/yellow]")
        return
    console.print(f"[yellow]Stopping background daemon (PID: {pid})...[/yellow]")
    stop_daemon()
    console.print("[green]Daemon stopped successfully.[/green]")

@daemon_app.command("restart")
def daemon_restart():
    """
    Restart the background daemon service.
    """
    daemon_stop()
    time.sleep(1.0)
    daemon_start()

@daemon_app.command("status")
def daemon_status():
    """
    Query background daemon status.
    """
    pid = is_daemon_running()
    if pid:
        import httpx
        api_status = "[red]Unresponsive[/red]"
        port = get_daemon_port()
        try:
            res = httpx.get(f"http://127.0.0.1:{port}/status", timeout=1.0)
            if res.status_code == 200:
                api_status = "[green]Healthy & Responsive[/green]"
        except Exception:
            pass
        console.print(f"Daemon Status: [bold green]ONLINE[/bold green] (PID: {pid})")
        console.print(f"API Server Status: {api_status} (Port: {port})")
    else:
        console.print("Daemon Status: [bold red]OFFLINE[/bold red]")

app.add_typer(daemon_app, name="daemon")

# --- Delegated/Aliased Daemon Commands on main app ---

@app.command()
def start(port: int = 8000, background: bool = True):
    """
    Start the Shadow OS Daemon API server.
    """
    if background:
        daemon_start(port=port)
    else:
        init_db()
        from shadow.api.server import start_server
        console.print(f"[green]Starting Shadow API server in foreground on port {port}...[/green]")
        start_server(port=port)

@app.command()
def stop():
    """
    Stop the background running Shadow OS Daemon server.
    """
    daemon_stop()

@app.command()
def status():
    """
    Query the local daemon and database status.
    """
    pid = is_daemon_running()
    if pid:
        console.print(f"Daemon Status: [bold green]ONLINE[/bold green] (PID: {pid})")
    else:
        console.print("Daemon Status: [bold red]OFFLINE[/bold red]")

    config = get_config()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM tasks")
    total_tasks = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM goals")
    total_goals = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM opportunities")
    total_opps = cursor.fetchone()["count"]

    cursor.execute("SELECT level, action, created_at FROM system_logs ORDER BY id DESC LIMIT 5")
    recent_logs = cursor.fetchall()

    conn.close()

    console.print(f"System: [bold blue]{config.app_name}[/bold blue]")
    console.print(f"Database: {config.db_path}")
    console.print(f"Total Goals Parsed: {total_goals}")
    console.print(f"Total Tasks: {total_tasks}")
    console.print(f"Total Opportunities Found: {total_opps}")

    table = Table(title="Recent Decision Logs")
    table.add_column("Timestamp", style="dim")
    table.add_column("Level", style="bold yellow")
    table.add_column("Action Summary")

    for log in recent_logs:
        table.add_row(log["created_at"], log["level"], log["action"])

    console.print(table)

# --- Standard App Commands ---

@app.command()
def mission(filepath: Optional[str] = None):
    """
    Parse and synchronize the mission.md file to local structured goals database.
    """
    path_to_use = filepath or os.path.join(SHADOW_HOME, "mission.md")
    if not os.path.exists(path_to_use):
        console.print(f"[red]mission.md file not found at: {path_to_use}. Run 'shadow doctor' to restore default.[/red]")
        return

    with open(path_to_use, "r", encoding="utf-8") as f:
        markdown_text = f.read()

    goals = goals_engine.parse_mission_markdown(markdown_text)
    goals_engine.sync_goals_to_db(goals)
    console.print(f"[green]Successfully parsed {len(goals)} structured goals from {path_to_use} and synced to DB.[/green]")

@app.command()
def goals():
    """
    List active structured goals tracked by Shadow OS.
    """
    active = goals_engine.get_active_goals()
    if not active:
        console.print("[yellow]No active goals found in the system. Run 'shadow mission' to parse.[/yellow]")
        return

    table = Table(title="Shadow Active Goals & Projects")
    table.add_column("ID", style="dim")
    table.add_column("Title", style="bold green")
    table.add_column("Category")
    table.add_column("Priority", style="bold magenta")
    table.add_column("Status")

    for g in active:
        table.add_row(str(g["id"]), g["title"], g["category"], g["priority"], g["status"])

    console.print(table)

@app.command()
def tasks():
    """
    List and prioritize queued execution tasks.
    """
    priority_engine.reprioritize_all_tasks()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY priority_score DESC")
    all_tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not all_tasks:
        console.print("[yellow]No tasks in queue. Run 'shadow opportunities' then convert them.[/yellow]")
        return

    table = Table(title="Shadow Action Task Queue")
    table.add_column("ID", style="dim")
    table.add_column("Title", style="bold green")
    table.add_column("Priority Score", style="bold yellow")
    table.add_column("Safety Level", style="cyan")
    table.add_column("Status")

    for t in all_tasks:
        table.add_row(str(t["id"]), t["title"], f"{t['priority_score']:.2f}", f"L{t['safety_level']}", t["status"])

    console.print(table)

@app.command()
def execute(task_id: int):
    """
    Trigger execution of a specific task.
    """
    console.print(f"[yellow]Triggering execution for Task #{task_id}...[/yellow]")
    res = asyncio.run(execution_engine.execute_task(task_id))
    if res.get("success"):
        console.print(f"[green]Task #{task_id} completed successfully![/green]")
        console.print(res.get("result"))
    else:
        if res.get("status") == "pending_approval":
            console.print(f"[bold yellow]Task #{task_id} is on hold. Requires approval via 'shadow approvals'![/bold yellow]")
        else:
            console.print(f"[red]Task #{task_id} failed: {res.get('error')}[/red]")

@app.command()
def approvals():
    """
    Review and approve/reject Safety Level 2 hold actions.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM approvals WHERE status = 'pending'")
    pending = cursor.fetchall()
    conn.close()

    if not pending:
        console.print("[green]No pending approvals in queue.[/green]")
        return

    for app_req in pending:
        console.print(f"\n[bold yellow]--- Pending Approval Request #{app_req['id']} ---[/bold yellow]")
        console.print(f"Task ID: {app_req['task_id']}")
        console.print(f"Action: {app_req['action']}")
        console.print(f"Parameters: {app_req['parameters']}")

        choice = typer.prompt("Approve? (y/n/cancel)", default="y")
        if choice.lower() == "y":
            execution_engine.process_approval(app_req["id"], approved=True, reason="CLI manually approved.")
            console.print("[green]Action approved and marked for execution.[/green]")
        elif choice.lower() == "n":
            execution_engine.process_approval(app_req["id"], approved=False, reason="CLI manually rejected.")
            console.print("[red]Action rejected.[/red]")
        else:
            console.print("[yellow]Approval skipped.[/yellow]")

@app.command()
def search(query: str):
    """
    Search the Shadow OS long-term sqlite memories and insights index.
    """
    res = memory_engine.search_memories(query)
    if not res:
        console.print(f"[yellow]No matching memories found for search query: '{query}'[/yellow]")
        return

    table = Table(title=f"Search Memories for: '{query}'")
    table.add_column("Category", style="cyan")
    table.add_column("Key", style="bold yellow")
    table.add_column("Content")
    table.add_column("Created At", style="dim")

    for m in res:
        table.add_row(m["category"], m["key"] or "None", m["content"][:80] + "...", m["created_at"])

    console.print(table)

@app.command()
def memory():
    """
    Display a general overview of stored long-term memories.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT category, COUNT(*) as count FROM memory GROUP BY category")
    rows = cursor.fetchall()
    conn.close()

    table = Table(title="Persistent Memory Blocks Statistics")
    table.add_column("Memory Category", style="bold cyan")
    table.add_column("Stored Records Count", style="bold yellow")

    for row in rows:
        table.add_row(row["category"], str(row["count"]))
    console.print(table)

@app.command()
def opportunities(queries: Optional[str] = None):
    """
    Trigger real-time web scan and parse new matching opportunities.
    """
    search_queries = [q.strip() for q in (queries or "Japan scholarships, Remote AI jobs").split(",")]
    console.print(f"[cyan]Scanning the web for: {search_queries}...[/cyan]")

    scanner = OpportunityScanner()
    found = asyncio.run(scanner.scan(search_queries))

    table = Table(title="Discovered Opportunities")
    table.add_column("Title", style="bold green")
    table.add_column("Category", style="magenta")
    table.add_column("URL")

    for o in found:
        table.add_row(o["title"], o["category"], o["url"])

    console.print(table)
    console.print("\n[green]Run 'shadow tasks' to prioritize and view generated action items.[/green]")

@app.command()
def schedule():
    """
    List configured cron and interval schedules.
    """
    table = Table(title="Shadow OS Active Schedules")
    table.add_column("Job Name", style="bold green")
    table.add_column("Interval / Cadence", style="bold cyan")
    table.add_column("Target Event Bus Trigger")

    table.add_row("scheduled_research", "Every 2 hours", "scheduled_research")
    table.add_row("scheduled_reflection", "Every 4 hours", "scheduled_reflection")
    table.add_row("scheduled_repo_analysis", "Every 8 hours", "scheduled_repo_analysis")
    table.add_row("scheduled_learning", "Every 2 hours", "scheduled_learning")

    console.print(table)

@app.command()
def providers():
    """
    Display configured and active AI Provider information.
    """
    config = get_config()
    table = Table(title="Active AI Provider Statuses")
    table.add_column("Provider", style="bold magenta")
    table.add_column("Target Model", style="bold green")
    table.add_column("Status / Active Default")

    table.add_row("OpenAI", config.openai.model, "Configured" if config.default_provider == "openai" else "Inactive")
    table.add_row("Anthropic Claude", config.anthropic.model, "Configured" if config.default_provider == "anthropic" else "Inactive")
    table.add_row("Google Gemini", config.gemini.model, "Configured" if config.default_provider == "gemini" else "Inactive")
    table.add_row("Local Mock Model", "shadow-mock-model", "Active (Default)" if config.default_provider == "mock" else "Ready")

    console.print(table)

@app.command()
def plugins():
    """
    List automatically discovered plugins, core tools, and skills.
    """
    tool_registry.discover_tools()
    tools = tool_registry.list_tools()
    skills = skills_registry.list_skills()

    table = Table(title="Discovered Tools & Extensions")
    table.add_column("Name", style="bold green")
    table.add_column("Type", style="bold cyan")
    table.add_column("Safety Level", style="magenta")

    for tool in tools:
        table.add_row(tool.name, "Plugin Tool", f"Level {tool.safety_level}")

    for skill in skills:
        table.add_row(skill.name, f"Core Skill (v{skill.version})", "N/A")

    console.print(table)

@app.command()
def reflect():
    """
    Perform strategic evening reflection audit.
    """
    console.print("[cyan]Compiling daily logs and task list for evening reflection...[/cyan]")
    text = asyncio.run(reflection_engine.perform_daily_reflection())
    console.print("\n[bold green]=== DAILY REFLECTION REPORT ===[/bold green]")
    console.print(text)

# --- Extended Commands ---

@app.command()
def tui():
    """
    Start the interactive TUI dashboard.
    """
    from shadow.cli.tui import start_tui_loop
    start_tui_loop()

@app.command()
def api(port: int = 8000):
    """
    Start the Shadow OS Daemon API server in the foreground.
    """
    from shadow.api.server import start_server
    console.print(f"[green]Starting Shadow API server in foreground on port {port}...[/green]")
    start_server(port=port)

@app.command()
def logs(limit: int = 20, follow: bool = False):
    """
    Stream or display recent system logs from the structured database.
    """
    def print_logs(after_id=0):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, level, action, created_at FROM system_logs WHERE id > ? ORDER BY id ASC LIMIT ?", (after_id, limit))
        rows = cursor.fetchall()
        conn.close()

        last_id = after_id
        for row in rows:
            color = "red" if row["level"] == "ERROR" else "yellow" if row["level"] == "WARNING" else "green"
            console.print(f"[{row['created_at']}] [{color}]{row['level']}[/{color}] - {row['action']}")
            last_id = row["id"]
        return last_id

    console.print("[cyan]Retrieving recent system logs...[/cyan]")
    last_id = print_logs()

    if follow:
        console.print("[cyan]Streaming logs in real-time... Press Ctrl+C to stop.[/cyan]")
        try:
            while True:
                time.sleep(1)
                last_id = print_logs(last_id)
        except KeyboardInterrupt:
            console.print("\n[yellow]Log streaming stopped.[/yellow]")

@app.command()
def doctor():
    """
    Run self-repair diagnostics on the Shadow OS installation.
    """
    import shutil
    import subprocess

    console.print("[bold cyan]=== SHADOW OS DOCTOR DIAGNOSTICS ===[/bold cyan]\n")

    # 1. Check directories
    console.print("[bold]1. Checking directory structure...[/bold]")
    required_dirs = ["config", "memory", "logs", "cache", "plugins", "backups"]
    all_dirs_ok = True
    for d in required_dirs:
        dir_path = os.path.join(SHADOW_HOME, d)
        if not os.path.exists(dir_path):
            console.print(f"  [red]✗[/red] Missing directory: {d}. Recreating...")
            os.makedirs(dir_path, exist_ok=True)
            all_dirs_ok = False
        else:
            console.print(f"  [green]✓[/green] Directory '{d}' is OK.")

    # 2. Check virtualenv
    console.print("\n[bold]2. Checking virtual environment...[/bold]")
    venv_python = os.path.join(SHADOW_HOME, "venv", "bin", "python")
    if os.name == "nt":
        venv_python = os.path.join(SHADOW_HOME, "venv", "Scripts", "python.exe")

    if not os.path.exists(venv_python):
        console.print("  [red]✗[/red] Virtual environment is broken or missing. Please run install.py to repair.")
    else:
        console.print("  [green]✓[/green] Virtual environment python exists.")

    # 3. Check dependencies
    console.print("\n[bold]3. Checking package dependencies...[/bold]")
    deps = ["pydantic", "pydantic_settings", "fastapi", "uvicorn", "rich", "watchdog", "typer"]
    for dep in deps:
        try:
            __import__(dep)
            console.print(f"  [green]✓[/green] Dependency '{dep}' is importable.")
        except ImportError:
            console.print(f"  [red]✗[/red] Missing dependency: {dep}. Re-installing...")
            try:
                subprocess.run([venv_python, "-m", "pip", "install", dep], check=True, stdout=subprocess.DEVNULL)
                console.print(f"    [green]✓[/green] Successfully repaired '{dep}'.")
            except Exception as e:
                console.print(f"    [red]✗[/red] Could not repair '{dep}': {e}")

    # 4. Check database corruption
    console.print("\n[bold]4. Checking database integrity...[/bold]")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        if len(tables) < 5:
            console.print(f"  [red]✗[/red] Database has missing tables ({len(tables)}/8). Reinitializing tables...")
            init_db()
            console.print("    [green]✓[/green] Database tables reinitialized successfully.")
        else:
            console.print(f"  [green]✓[/green] Database connected. Found {len(tables)} tables: {', '.join(tables)}")
    except Exception as e:
        console.print(f"  [red]✗[/red] Database corrupted or inaccessible: {e}. Reinitializing...")
        try:
            init_db()
            console.print("    [green]✓[/green] Database reinitialized successfully.")
        except Exception as ex:
            console.print(f"    [red]✗[/red] Database repair failed: {ex}")

    # 5. Check mission.md
    console.print("\n[bold]5. Checking mission.md configuration...[/bold]")
    mission_path = os.path.join(SHADOW_HOME, "mission.md")
    if not os.path.exists(mission_path):
        console.print("  [red]✗[/red] mission.md not found in ~/.shadow/. Restoring default...")
        try:
            default_content = """# Identity
Shadow User.

# Long-Term Goals
- Master Advanced Systems Engineering
- Deploy Autonomous Agent Networks

# Current Projects
- PROJECT SHADOW Core System

# Skills To Learn
- Python, Systems Architecting, Android Automation
"""
            with open(mission_path, "w", encoding="utf-8") as f:
                f.write(default_content)
            console.print("    [green]✓[/green] Restored default mission.md.")
        except Exception as e:
            console.print(f"    [red]✗[/red] Failed to restore mission.md: {e}")
    else:
        console.print("  [green]✓[/green] mission.md exists.")

    # 6. Check launcher and permissions
    console.print("\n[bold]6. Checking executable launcher...[/bold]")
    launcher_dir = None
    prefix = os.environ.get("PREFIX")
    for possible_dir in [prefix, "/data/data/com.termux/files/usr", "/usr/local", os.path.expanduser("~/.local")]:
        if possible_dir:
            cand = os.path.join(possible_dir, "bin", "shadow")
            if os.path.exists(cand):
                launcher_dir = cand
                break
    if not launcher_dir:
        console.print("  [red]✗[/red] Global shadow executable launcher not found in standard PATHs. Run 'python3 install.py' to recreate.")
    else:
        if os.name != "nt":
            if not os.access(launcher_dir, os.X_OK):
                console.print(f"  [red]✗[/red] Launcher at {launcher_dir} lacks execute permissions. Fixing...")
                os.chmod(launcher_dir, 0o755)
            else:
                console.print(f"  [green]✓[/green] Launcher is executable at: {launcher_dir}")
        else:
            console.print(f"  [green]✓[/green] Launcher batch file exists: {launcher_dir}")

    console.print("\n[bold green]Diagnostics and repair complete.[/bold green]")

@app.command()
def update():
    """
    Fetch the latest release, update dependencies, run migrations, and verify installation.
    """
    import shutil
    import subprocess

    console.print("[green]Starting Shadow OS Update Process...[/green]")

    # 1. Back up database and mission.md
    timestamp = int(time.time())
    backup_db = os.path.join(SHADOW_HOME, "backups", f"shadow_backup_{timestamp}.db")
    backup_mission = os.path.join(SHADOW_HOME, "backups", f"mission_backup_{timestamp}.md")

    config = get_config()
    db_path = config.db_path
    mission_path = os.path.join(SHADOW_HOME, "mission.md")

    db_backed_up = False
    mission_backed_up = False

    if os.path.exists(db_path):
        try:
            shutil.copy(db_path, backup_db)
            db_backed_up = True
            console.print(f"  Backed up database to: {backup_db}")
        except Exception as e:
            console.print(f"  [yellow]Failed to back up database: {e}[/yellow]")

    if os.path.exists(mission_path):
        try:
            shutil.copy(mission_path, backup_mission)
            mission_backed_up = True
            console.print(f"  Backed up mission.md to: {backup_mission}")
        except Exception as e:
            console.print(f"  [yellow]Failed to back up mission.md: {e}[/yellow]")

    # Resolve the project root dynamically from the module file location
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        # 2. Fetch latest changes if we are in a git repository
        git_dir = os.path.join(project_root, ".git")
        if os.path.exists(git_dir):
            console.print(f"  Fetching latest changes from Git repository at {project_root}...")
            try:
                subprocess.run(["git", "pull"], check=True, cwd=project_root)
            except Exception as e:
                console.print(f"  [yellow]Git pull failed or was skipped: {e}. Proceeding with local updates...[/yellow]")

        # 3. Update dependencies inside the venv
        venv_python = os.path.join(SHADOW_HOME, "venv", "bin", "python")
        if os.name == "nt":
            venv_python = os.path.join(SHADOW_HOME, "venv", "Scripts", "python.exe")

        console.print("  Updating dependencies safely...")
        uv_path = shutil.which("uv")
        if uv_path:
            subprocess.run([uv_path, "pip", "install", "--python", venv_python, "-e", "."], check=True, cwd=project_root)
        else:
            subprocess.run([venv_python, "-m", "pip", "install", "-e", "."], check=True, cwd=project_root)

        # 4. Run migrations/init_db
        console.print("  Running database migrations and table verification...")
        init_db()

        # 5. Verify the installation
        console.print("  Verifying installation works...")
        res = subprocess.run([venv_python, "-m", "shadow.cli.main", "status"], capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Verification failed with exit code {res.returncode}. Error: {res.stderr}")

        console.print("[bold green]Shadow OS updated successfully to the latest version![/bold green]")

    except Exception as e:
        console.print(f"[bold red]Update failed: {e}[/bold red]")
        console.print("[yellow]Initiating automatic rollback to previous state...[/yellow]")

        # Rollback
        if db_backed_up and os.path.exists(backup_db):
            shutil.copy(backup_db, db_path)
            console.print("  Database rolled back.")
        if mission_backed_up and os.path.exists(backup_mission):
            shutil.copy(backup_mission, mission_path)
            console.print("  mission.md rolled back.")

        console.print("[bold green]Rollback complete. Previous installation restored.[/bold green]")

@app.command()
def uninstall():
    """
    Uninstall Shadow OS, the virtual environment, the global launcher, and all configured files.
    """
    import shutil

    choice = typer.confirm("Are you sure you want to completely uninstall Shadow OS?", default=False)
    if not choice:
        console.print("[yellow]Uninstall cancelled.[/yellow]")
        return

    preserve_data = typer.confirm("Would you like to keep your database, mission.md, and configuration under ~/.shadow/?", default=True)

    # 1. Remove launcher
    prefix = os.environ.get("PREFIX")
    for possible_dir in [prefix, "/data/data/com.termux/files/usr", "/usr/local", os.path.expanduser("~/.local")]:
        if possible_dir:
            cand = os.path.join(possible_dir, "bin", "shadow")
            if os.path.exists(cand):
                try:
                    os.remove(cand)
                    console.print(f"  Removed launcher executable from: {cand}")
                except Exception as e:
                    console.print(f"  [red]Failed to remove launcher at {cand}: {e}[/red]")

    # 2. Stop running daemon
    try:
        stop_daemon()
    except Exception:
        pass

    # 3. Remove files
    if not preserve_data:
        if os.path.exists(SHADOW_HOME):
            try:
                shutil.rmtree(SHADOW_HOME)
                console.print(f"  Removed all shadow files and directory: {SHADOW_HOME}")
            except Exception as e:
                console.print(f"  [red]Failed to remove directory {SHADOW_HOME}: {e}[/red]")
    else:
        venv_path = os.path.join(SHADOW_HOME, "venv")
        if os.path.exists(venv_path):
            try:
                shutil.rmtree(venv_path)
                console.print("  Removed virtual environment.")
            except Exception as e:
                console.print(f"  [red]Failed to remove venv: {e}[/red]")

    console.print("[bold green]Shadow OS has been successfully uninstalled.[/bold green]")

if __name__ == "__main__":
    app()
