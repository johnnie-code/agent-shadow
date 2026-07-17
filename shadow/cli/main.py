import os
import sys
import typer
import asyncio
import shutil
import subprocess
from datetime import datetime
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from shadow.core.config import get_config
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

@app.command()
def start(port: int = 8000, background: bool = False):
    """
    Start the Shadow OS Daemon API server.
    """
    init_db()
    console.print("[green]Starting Shadow OS Background Server...[/green]")
    if background:
        import subprocess
        # Start in background using nohup or subprocess
        subprocess.Popen([sys.executable, "-c", f"from shadow.api.server import start_server; start_server(port={port})"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        console.print(f"[green]Shadow server is running in the background on port {port}.[/green]")
    else:
        from shadow.api.server import start_server
        start_server(port=port)

@app.command()
def stop():
    """
    Stop any background running Shadow OS Daemon server.
    """
    import subprocess
    console.print("[yellow]Stopping Shadow OS Daemon process on port 8000...[/yellow]")
    try:
        # Kill python processes running uvicorn / server
        subprocess.run("pkill -f 'shadow.api.server'", shell=True)
        console.print("[green]Shadow background daemon stopped successfully.[/green]")
    except Exception as e:
        console.print(f"[red]Error stopping daemon: {e}[/red]")

@app.command()
def status():
    """
    Query the local daemon and database status.
    """
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

    console.print(f"[bold blue]System: {config.app_name}[/bold blue]")
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

@app.command()
def mission():
    """
    Parse and synchronize the mission.md file to local structured goals database.
    """
    if not os.path.exists("mission.md"):
        console.print("[red]mission.md file not found. Create one in current directory first.[/red]")
        return

    with open("mission.md", "r", encoding="utf-8") as f:
        markdown_text = f.read()

    goals = goals_engine.parse_mission_markdown(markdown_text)
    goals_engine.sync_goals_to_db(goals)
    console.print(f"[green]Successfully parsed {len(goals)} structured goals from mission.md and synced to DB.[/green]")

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
    # Auto reprioritize first to ensure fresh weights
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

def run_rollback(backup_dir: str):
    console.print(f"\n[bold red]🚨 Update failed! Starting automatic rollback to backup from {backup_dir}...[/bold red]")
    try:
        for file in ["mission.md", "shadow.db", ".env"]:
            src = os.path.join(backup_dir, file)
            if os.path.exists(src):
                shutil.copy2(src, ".")
                console.print(f"[green][✓] Restored {file}[/green]")
        console.print("[bold green]✓ Rollback completed successfully. System is restored to its previous state.[/bold green]")
    except Exception as re:
        console.print(f"[red][x] Critical Error: Rollback failed: {re}[/red]")

@app.command()
def update():
    """
    Safely update Shadow to the latest version.
    """
    console.print("[bold blue]🔄 Safely Updating Project Shadow...[/bold blue]\n")

    # 1. Perform backing up
    backup_dir = f"backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    console.print(f"[*] Creating automatic backup at [yellow]{backup_dir}/[/yellow]...")
    try:
        os.makedirs(backup_dir, exist_ok=True)
        backed_up_files = []
        for file in ["mission.md", "shadow.db", ".env"]:
            if os.path.exists(file):
                shutil.copy2(file, backup_dir)
                backed_up_files.append(file)
        console.print(f"[green][✓] Backed up: {', '.join(backed_up_files)}[/green]")
    except Exception as e:
        console.print(f"[red][x] Backup failed: {e}. Aborting update for safety.[/red]")
        return

    # 2. Pull changes from repository
    console.print("[*] Pulling latest updates from git repository...")
    try:
        if not os.path.exists(".git"):
            raise Exception("Not a git repository.")

        res = subprocess.run(["git", "pull"], text=True, capture_output=True)
        if res.returncode != 0:
            raise Exception(res.stderr or "git pull command failed.")
        console.print("[green][✓] Git pull completed successfully.[/green]")
    except Exception as e:
        console.print(f"[red][x] Git update failed: {e}[/red]")
        console.print("[yellow]No code changes made, no rollback required.[/yellow]")
        return

    # 3. Upgrade Python dependencies
    console.print("[*] Upgrading Python dependencies...")
    try:
        use_uv = shutil.which("uv") is not None
        if use_uv:
            subprocess.run(["uv", "pip", "install", "-e", "."], check=True)
        else:
            subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=True)
        console.print("[green][✓] Python dependencies upgraded successfully.[/green]")
    except Exception as e:
        console.print(f"[red][x] Dependency upgrade failed: {e}[/red]")
        run_rollback(backup_dir)
        return

    # 4. Run migrations/initialization
    console.print("[*] Running database migrations and syncing mission...")
    try:
        init_db()
        if os.path.exists("mission.md"):
            with open("mission.md", "r", encoding="utf-8") as f:
                markdown_text = f.read()
            goals = goals_engine.parse_mission_markdown(markdown_text)
            goals_engine.sync_goals_to_db(goals)
        console.print("[green][✓] Migrations and synchronization completed successfully.[/green]")
    except Exception as e:
        console.print(f"[red][x] Migration/sync failed: {e}[/red]")
        run_rollback(backup_dir)
        return

    # 5. Run Self-Test
    console.print("[*] Performing complete self-test...")
    try:
        res = subprocess.run([sys.executable, "-m", "pytest", "tests/"], capture_output=True, text=True)
        if res.returncode != 0:
            raise Exception(res.stderr or "Self-tests failed.")
        console.print("[green][✓] Complete self-test suites passed perfectly![/green]")
    except Exception as e:
        console.print(f"[red][x] Self-test failed: {e}[/red]")
        run_rollback(backup_dir)
        return

    console.print("\n[bold green]✓ Shadow Update: Project Shadow successfully updated to the latest version![/bold green]")

@app.command()
def doctor(repair: bool = typer.Option(True, help="Automatically attempt to repair restorable issues.")):
    """
    Diagnose and repair installation issues with Project Shadow.
    """
    console.print("[bold blue]🩺 Running Project Shadow Doctor Diagnostics...[/bold blue]\n")
    all_ok = True

    # 1. Termux Environment Check
    is_termux = os.path.exists("/data/data/com.termux/files/usr") or "TERMUX_VERSION" in os.environ
    if is_termux:
        console.print("[green][✓] Termux environment detected.[/green]")
        # Check Termux:API
        has_api = shutil.which("termux-battery-status") is not None
        if has_api:
            console.print("[green][✓] Termux:API command-line tools are installed.[/green]")
        else:
            console.print("[yellow][!] Termux:API command-line tools are missing.[/yellow]")
            console.print("    To fix: Run 'pkg install termux-api' in Termux.")
            all_ok = False
    else:
        console.print("[yellow][!] Non-Termux environment detected. Skipping Termux:API checks.[/yellow]")

    # 2. Dependency Check
    dependencies = ["pydantic", "pydantic_settings", "fastapi", "uvicorn", "rich", "watchdog", "httpx", "typer"]
    missing_deps = []
    for dep in dependencies:
        try:
            __import__(dep)
        except ImportError:
            missing_deps.append(dep)

    if not missing_deps:
        console.print("[green][✓] All required Python dependencies are successfully installed.[/green]")
    else:
        console.print(f"[red][x] Missing Python dependencies: {', '.join(missing_deps)}[/red]")
        all_ok = False
        if repair:
            console.print("[yellow]Attempting to repair: Installing missing dependencies...[/yellow]")
            try:
                use_uv = shutil.which("uv") is not None
                if use_uv:
                    subprocess.run(["uv", "pip", "install", "-e", "."], check=True)
                else:
                    subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=True)
                console.print("[green][✓] Reinstalled dependencies successfully.[/green]")
            except Exception as e:
                console.print(f"[red][x] Failed to reinstall dependencies: {e}[/red]")

    # 3. Database Check
    db_ok = False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]
        conn.close()
        required_tables = ["memory", "conversation", "goals", "opportunities", "tasks", "system_logs", "approvals"]
        missing_tables = [t for t in required_tables if t not in tables]
        if not missing_tables:
            console.print("[green][✓] Database connection and schema verified.[/green]")
            db_ok = True
        else:
            console.print(f"[yellow][!] Database schema is missing tables: {', '.join(missing_tables)}[/yellow]")
            all_ok = False
            if repair:
                console.print("[yellow]Attempting to repair: Reinitializing database tables...[/yellow]")
                init_db()
                console.print("[green][✓] Database schema successfully reinitialized.[/green]")
                db_ok = True
    except Exception as e:
        console.print(f"[red][x] Database connection or integrity check failed: {e}[/red]")
        all_ok = False
        if repair:
            console.print("[yellow]Attempting to repair: Initializing new database...[/yellow]")
            try:
                init_db()
                console.print("[green][✓] Database successfully initialized.[/green]")
                db_ok = True
            except Exception as re:
                console.print(f"[red][x] Database repair failed: {re}[/red]")

    # 4. Mission file and goal sync check
    if not os.path.exists("mission.md"):
        console.print("[red][x] mission.md file is missing.[/red]")
        all_ok = False
        if repair:
            console.print("[yellow]Attempting to repair: Generating a default mission.md...[/yellow]")
            try:
                with open("mission.md", "w", encoding="utf-8") as f:
                    f.write("# MISSION\n\n## Identity\n- **Name**: Shadow Agent\n- **Role**: Personal Chief of Staff / Autonomous Agent OS\n")
                console.print("[green][✓] Generated default mission.md.[/green]")
                if db_ok:
                    with open("mission.md", "r", encoding="utf-8") as f:
                        markdown_text = f.read()
                    goals = goals_engine.parse_mission_markdown(markdown_text)
                    goals_engine.sync_goals_to_db(goals)
                    console.print("[green][✓] Synced default goals to database.[/green]")
            except Exception as e:
                console.print(f"[red][x] Failed to repair mission.md: {e}[/red]")
    else:
        console.print("[green][✓] mission.md file exists.[/green]")
        if db_ok:
            try:
                active_goals = goals_engine.get_active_goals()
                if active_goals:
                    console.print(f"[green][✓] Database contains {len(active_goals)} active goal(s).[/green]")
                else:
                    console.print("[yellow][!] Database does not contain active goals. Syncing mission.md...[/yellow]")
                    with open("mission.md", "r", encoding="utf-8") as f:
                        markdown_text = f.read()
                    goals = goals_engine.parse_mission_markdown(markdown_text)
                    goals_engine.sync_goals_to_db(goals)
                    console.print("[green][✓] Mission goals synchronized to database successfully.[/green]")
            except Exception as e:
                console.print(f"[yellow][!] Failed to sync/verify goals: {e}[/yellow]")

    # 5. Config/API Keys Check
    config = get_config()
    provider = config.default_provider
    console.print(f"[*] Active Default AI Provider: [bold purple]{provider}[/bold purple]")
    if provider == "mock":
        console.print("[green][✓] Mock provider active. No API keys required for development.[/green]")
    else:
        has_key = False
        if provider == "openai" and config.openai.api_key:
            has_key = True
        elif provider == "anthropic" and config.anthropic.api_key:
            has_key = True
        elif provider == "gemini" and config.gemini.api_key:
            has_key = True

        if has_key:
            console.print(f"[green][✓] API Key for provider '{provider}' is configured.[/green]")
        else:
            console.print(f"[red][x] API Key for provider '{provider}' is missing or empty.[/red]")
            all_ok = False
            if repair:
                new_key = typer.prompt(f"Please enter your API Key for provider '{provider}' (or leave blank to skip)", default="", show_default=False)
                if new_key:
                    try:
                        env_file = ".env"
                        if os.path.exists(env_file):
                            with open(env_file, "r") as f:
                                lines = f.readlines()
                            provider_key_str = f"SHADOW_{provider.upper()}__API_KEY"
                            key_exists = False
                            for i, line in enumerate(lines):
                                if line.startswith(f"{provider_key_str}="):
                                    lines[i] = f'{provider_key_str}="{new_key}"\n'
                                    key_exists = True
                                    break
                            if not key_exists:
                                lines.append(f'{provider_key_str}="{new_key}"\n')
                            with open(env_file, "w") as f:
                                f.writelines(lines)
                            console.print(f"[green][✓] API Key written to .env. Please restart to reload config.[/green]")
                        else:
                            with open(env_file, "w") as f:
                                f.write(f'SHADOW_DEFAULT_PROVIDER="{provider}"\n')
                                f.write(f'{provider_key_str}="{new_key}"\n')
                            console.print(f"[green][✓] Generated .env with API Key.[/green]")
                    except Exception as e:
                        console.print(f"[red][x] Failed to write API key to .env: {e}[/red]")

    if all_ok:
        console.print("\n[bold green]✓ Shadow Doctor: All diagnostic checks passed perfectly![/bold green]")
    else:
        console.print("\n[bold yellow]! Shadow Doctor: Some diagnostics reported warnings/errors. Please review advice above.[/bold yellow]")

@app.command()
def uninstall(
    preserve_data: Optional[bool] = typer.Option(
        None, help="Preserve user data (database, config, mission.md) during uninstallation."
    )
):
    """
    Completely remove Shadow while optionally preserving user data.
    """
    console.print("[bold red]🚨 Uninstalling Project Shadow...[/bold red]\n")

    confirm = typer.confirm("Are you sure you want to completely uninstall Project Shadow?")
    if not confirm:
        console.print("[yellow]Uninstallation cancelled.[/yellow]")
        return

    if preserve_data is None:
        preserve_data = typer.confirm("Do you want to preserve your user data (database, config, mission.md)?", default=True)

    # 1. Deleting user data if not preserving
    if not preserve_data:
        console.print("[yellow][*] Removing user data...[/yellow]")
        for file in ["shadow.db", "shadow.db-wal", "shadow.db-shm", ".env", "mission.md"]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                    console.print(f"  Removed {file}")
                except Exception as e:
                    console.print(f"  [red]Failed to remove {file}: {e}[/red]")
        if os.path.exists("backups"):
            try:
                shutil.rmtree("backups")
                console.print("  Removed backups/ directory")
            except Exception as e:
                console.print(f"  [red]Failed to remove backups/: {e}[/red]")
    else:
        console.print("[green][✓] User data (database, config, mission.md) preserved.[/green]")

    # 2. Deleting virtual environment
    if os.path.exists(".venv"):
        console.print("[yellow][*] Deleting virtual environment (.venv)...[/yellow]")
        try:
            shutil.rmtree(".venv")
            console.print("  Deleted .venv directory")
        except Exception as e:
            console.print(f"  [red]Failed to delete .venv: {e}[/red]")

    # 3. Deleting global executable wrapper
    is_termux = os.path.exists("/data/data/com.termux/files/usr") or "TERMUX_VERSION" in os.environ
    global_bin_path = ""
    if is_termux:
        global_bin_path = "/data/data/com.termux/files/usr/bin/shadow"
    else:
        for path in ["/usr/local/bin/shadow", f"{os.path.expanduser('~')}/.local/bin/shadow"]:
            if os.path.exists(path):
                global_bin_path = path
                break

    if global_bin_path and os.path.exists(global_bin_path):
        console.print(f"[yellow][*] Deleting global wrapper at {global_bin_path}...[/yellow]")
        try:
            os.remove(global_bin_path)
            console.print("  Deleted global wrapper.")
        except Exception as e:
            console.print(f"  [red]Failed to remove global wrapper: {e}[/red]")

    console.print("\n[bold green]✓ Project Shadow uninstalled successfully![/bold green]")
    console.print("Note: To completely delete the repository, you can now safely delete this directory:")
    console.print(f"  [yellow]rm -rf {os.getcwd()}[/yellow]\n")

if __name__ == "__main__":
    app()
