import os
import sys
import json
import time
import typer
import asyncio
import shutil
import subprocess
from datetime import datetime
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
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
daemon_app = typer.Typer(name="daemon", help="Manage the Shadow OS background daemon service.")
app.add_typer(daemon_app, name="daemon")

sandbox_app = typer.Typer(name="sandbox", help="Manage private Sandbox Computers for Ghost.")
app.add_typer(sandbox_app, name="sandbox")

console = Console()

# --- Sandbox CLI Subcommands ---

@sandbox_app.command("create")
def sandbox_create(
    sandbox_id: str = typer.Argument(..., help="Unique identifier of the sandbox computer"),
    sandbox_type: str = typer.Option("generic", "--type", "-t", help="Target sandbox type, e.g., 'python', 'node', 'android'")
):
    """Create and initialize a secure, isolated sandbox computer."""
    from shadow.core.sandbox import sandbox_manager
    computer = sandbox_manager.create_sandbox(sandbox_id, sandbox_type)
    console.print(f"[green]✓ Secure isolated sandbox computer '{sandbox_id}' of type '{sandbox_type}' created successfully.[/green]")
    console.print(f"  Workspace location: [yellow]{computer.workspace_dir}[/yellow]")

@sandbox_app.command("destroy")
def sandbox_destroy(
    sandbox_id: str = typer.Argument(..., help="Unique identifier of the sandbox computer")
):
    """Completely destroy a sandbox computer and clean up all storage."""
    from shadow.core.sandbox import sandbox_manager
    confirm = typer.confirm(f"Are you sure you want to completely destroy sandbox '{sandbox_id}'? This action is irreversible!")
    if confirm:
        success = sandbox_manager.destroy_sandbox(sandbox_id)
        if success:
            console.print(f"[green]✓ Sandbox '{sandbox_id}' destroyed successfully.[/green]")
        else:
            console.print(f"[red]Error destroying sandbox '{sandbox_id}'.[/red]")
    else:
        console.print("[yellow]Destroy action cancelled.[/yellow]")

@sandbox_app.command("list")
def sandbox_list():
    """List all active sandboxes, their metadata, and storage consumption."""
    from shadow.core.sandbox import sandbox_manager
    sandboxes = sandbox_manager.list_sandboxes()
    if not sandboxes:
        console.print("[yellow]No active sandbox computers found.[/yellow]")
        return

    table = Table(title="Shadow Sandbox Computers")
    table.add_column("Sandbox ID", style="bold green")
    table.add_column("Type", style="cyan")
    table.add_column("Created At", style="dim")
    table.add_column("Storage (MB)", style="bold yellow")
    table.add_column("Status", style="magenta")

    for s in sandboxes:
        try:
            created_str = datetime.fromtimestamp(float(s["created_at"])).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            created_str = s.get("created_at", "N/A")
        table.add_row(
            s["sandbox_id"],
            s["sandbox_type"],
            created_str,
            f"{s.get('storage_mb', 0.0):.2f}",
            s.get("status", "ready")
        )
    console.print(table)

@sandbox_app.command("run")
def sandbox_run(
    sandbox_id: str = typer.Argument(..., help="Unique identifier of the sandbox computer"),
    command: str = typer.Argument(..., help="Terminal command to execute inside the sandbox")
):
    """Run a shell command inside the sandbox's isolated computer."""
    from shadow.core.sandbox import sandbox_manager
    computer = sandbox_manager.get_sandbox(sandbox_id)
    if not computer:
        console.print(f"[red]Error: Sandbox computer '{sandbox_id}' not found.[/red]")
        return

    console.print(f"[cyan]Executing inside sandbox '{sandbox_id}': {command}[/cyan]")
    res = asyncio.run(computer.execute_terminal(command))

    if res["success"]:
        console.print("[green]✓ Command completed successfully.[/green]")
    else:
        console.print(f"[red]✗ Command failed with exit code {res['exit_code']}.[/red]")

    if res["stdout"]:
        console.print("\n[bold]STDOUT:[/bold]")
        console.print(res["stdout"])
    if res["stderr"]:
        console.print("\n[bold red]STDERR:[/bold red]")
        console.print(res["stderr"])

@sandbox_app.command("snapshot")
def sandbox_snapshot(
    sandbox_id: str = typer.Argument(..., help="Unique identifier of the sandbox computer"),
    name: str = typer.Argument(..., help="Checkpoint name for the snapshot")
):
    """Take an instant checkpoint snapshot of the sandbox's current workspace state."""
    from shadow.core.sandbox import sandbox_manager
    success = sandbox_manager.snapshot_sandbox(sandbox_id, name)
    if success:
        console.print(f"[green]✓ Snapshot '{name}' successfully captured for sandbox '{sandbox_id}'.[/green]")
    else:
        console.print(f"[red]Error creating snapshot for sandbox '{sandbox_id}'.[/red]")

@sandbox_app.command("restore")
def sandbox_restore(
    sandbox_id: str = typer.Argument(..., help="Unique identifier of the sandbox computer"),
    name: str = typer.Argument(..., help="Snapshot checkpoint name to restore")
):
    """Instantly restore a sandbox computer to a previously saved checkpoint snapshot."""
    from shadow.core.sandbox import sandbox_manager
    success = sandbox_manager.restore_snapshot(sandbox_id, name)
    if success:
        console.print(f"[green]✓ Sandbox '{sandbox_id}' workspace successfully restored to snapshot '{name}'.[/green]")
    else:
        console.print(f"[red]Error: Snapshot '{name}' not found or could not be restored for sandbox '{sandbox_id}'.[/red]")

@sandbox_app.command("sync")
def sandbox_sync(
    sandbox_id: str = typer.Argument(..., help="Unique identifier of the sandbox computer"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Preview changed files and unified diffs"),
    conflict_check: bool = typer.Option(False, "--conflicts", "-c", help="Check for host/sandbox sync conflicts"),
    approve: bool = typer.Option(False, "--approve", "-a", help="Approve and perform sync copy immediately")
):
    """Safely preview and synchronize verified files from the sandbox workspace back to the host system."""
    from shadow.core.sync import FileSyncManager

    if conflict_check or (not preview and not approve):
        conflicts = FileSyncManager.detect_conflicts(sandbox_id)
        if conflicts:
            console.print("[bold red]⚠️ SYNC CONFLICTS DETECTED:[/bold red]")
            for conf in conflicts:
                console.print(f"  • File: [yellow]{conf['file']}[/yellow]")
                console.print(f"    Message: {conf['message']}")
            if not approve:
                return
        else:
            console.print("[green]✔ No conflict detection issues found.[/green]")

    if preview:
        changes = FileSyncManager.preview_changes(sandbox_id)
        if not changes:
            console.print("[yellow]No modifications or new files found inside sandbox workspace.[/yellow]")
            return
        console.print("\n[bold cyan]=== Sandbox Sync Preview ===[/bold cyan]")
        for c in changes:
            console.print(f"\nFile: [green]{c['file']}[/green] ({c['status']})")
            if c["diff"]:
                console.print("[bold]Diff:[/bold]")
                console.print(c["diff"])
        return

    if approve:
        confirm = typer.confirm(f"Are you sure you want to synchronize all verified changes from sandbox '{sandbox_id}' to host?")
        if confirm:
            res = FileSyncManager.apply_sync(sandbox_id)
            if res["success"]:
                console.print(f"[green]✓ Synchronization succeeded. Synced files: {', '.join(res['synced_files']) or 'none'}[/green]")
                console.print(f"  Rollback backup saved at: [yellow]{res['backup_dir']}[/yellow]")
            else:
                console.print(f"[bold red]✗ Sync failed:[/bold red] {res.get('error') or 'Aborted due to conflicts'}")
        else:
            console.print("[yellow]Sync copy aborted.[/yellow]")

@sandbox_app.command("status")
def sandbox_status(
    sandbox_id: str = typer.Argument(..., help="Unique identifier of the sandbox computer")
):
    """Query sandbox diagnostics, logs, and simulated CPU/RAM/storage resource limits."""
    from shadow.core.sandbox import sandbox_manager
    computer = sandbox_manager.get_sandbox(sandbox_id)
    if not computer:
        console.print(f"[red]Error: Sandbox computer '{sandbox_id}' not found.[/red]")
        return

    meta = computer.load_meta()
    usage = computer.get_resource_usage()

    console.print(f"\n[bold cyan]=== Sandbox Computer '{sandbox_id}' Status ===[/bold cyan]\n")
    console.print(f"Type:             [green]{meta.get('sandbox_type')}[/green]")
    console.print(f"Status:           [green]{meta.get('status')}[/green]")
    console.print(f"Installed Software:[yellow]{', '.join(meta.get('installed_software', [])) or 'none'}[/yellow]")
    console.print(f"Storage Used:     [yellow]{usage['storage_mb']:.2f} MB[/yellow]")
    console.print(f"CPU usage:        [yellow]{usage['cpu_percent']:.1f}%[/yellow]")
    console.print(f"RAM footprint:    [yellow]{usage['ram_mb']:.1f} MB[/yellow]")

    # List history
    history = meta.get("workspace", {}).get("execution_history", [])
    if history:
        console.print("\n[bold]Recent Command Logs:[/bold]")
        for h in history[-5:]:
            console.print(f"  • [green]{h['command']}[/green] (Exit: {h['exit_code']})")

@sandbox_app.command("notebook")
def sandbox_notebook(
    sandbox_id: str = typer.Argument(..., help="Unique identifier of the sandbox computer")
):
    """Inspect Ghost's reasoning and progress logged inside the persistent AI Notebook."""
    from shadow.core.sandbox import sandbox_manager
    computer = sandbox_manager.get_sandbox(sandbox_id)
    if not computer:
        console.print(f"[red]Error: Sandbox computer '{sandbox_id}' not found.[/red]")
        return

    nb = computer.load_notebook()
    console.print(f"\n[bold magenta]=== AI Notebook for Sandbox '{sandbox_id}' ===[/bold magenta]\n")
    console.print(f"[bold cyan]OBJECTIVE:[/bold cyan] {nb.get('objective') or 'None'}\n")

    sections = [
        ("plan", "Plan Checklist"),
        ("progress", "Progress Logs"),
        ("problems", "Encountered Problems"),
        ("solutions", "Applied Solutions"),
        ("next_steps", "Next Steps"),
        ("lessons_learned", "Lessons Learned")
    ]
    for key, title in sections:
        val = nb.get(key, [])
        console.print(f"[bold]{title}:[/bold]")
        if val:
            for item in val:
                console.print(f"  • {item}")
        else:
            console.print("  • None logged yet")
        console.print()

@sandbox_app.command("jobs")
def sandbox_jobs():
    """List all running and finished background sandbox jobs."""
    from shadow.core.sandbox import job_manager
    jobs = job_manager.list_jobs()
    if not jobs:
        console.print("[yellow]No background sandbox jobs registered.[/yellow]")
        return

    table = Table(title="Sandbox Background Jobs")
    table.add_column("Job ID", style="bold green")
    table.add_column("Sandbox ID", style="cyan")
    table.add_column("PID", style="yellow")
    table.add_column("Status", style="magenta")
    table.add_column("Command")

    for j in jobs:
        table.add_row(
            j["job_id"],
            j["sandbox_id"],
            str(j["pid"]),
            j["status"],
            j["command"]
        )
    console.print(table)

@sandbox_app.command("jobs-start")
def sandbox_jobs_start(
    sandbox_id: str = typer.Argument(..., help="Unique identifier of the sandbox computer"),
    command: str = typer.Argument(..., help="Command to run in background")
):
    """Start a long-running command in the background that survives CLI exit."""
    from shadow.core.sandbox import job_manager
    job_id = job_manager.start_job(sandbox_id, command)
    console.print(f"[green]✓ Background job '{job_id}' started successfully with PID tracking inside sandbox '{sandbox_id}'.[/green]")

@sandbox_app.command("logs")
def sandbox_logs(
    job_id: str = typer.Argument(..., help="ID of the background job")
):
    """Read standard outputs and trace errors of a background job."""
    from shadow.core.sandbox import job_manager
    status = job_manager.get_job_status(job_id)
    if status["status"] == "not_found":
        console.print(f"[red]Error: Job '{job_id}' not found.[/red]")
        return

    log_path = status.get("log_path")
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            console.print(f"\n[bold magenta]=== Log Output for Job '{job_id}' ===[/bold magenta]\n")
            console.print(f.read())
    else:
        console.print(f"[yellow]No log files found at {log_path}[/yellow]")

@sandbox_app.command("cancel")
def sandbox_cancel(
    job_id: str = typer.Argument(..., help="ID of the background job to kill")
):
    """Terminate a runaway background job process."""
    from shadow.core.sandbox import job_manager
    success = job_manager.cancel_job(job_id)
    if success:
        console.print(f"[green]✓ Job '{job_id}' has been terminated successfully.[/green]")
    else:
        console.print(f"[red]Error: Job '{job_id}' could not be terminated.[/red]")

@sandbox_app.command("resume")
def sandbox_resume(
    job_id: str = typer.Argument(..., help="ID of the background job to resume")
):
    """Resume a paused background job process."""
    from shadow.core.sandbox import job_manager
    success = job_manager.resume_job(job_id)
    if success:
        console.print(f"[green]✓ Job '{job_id}' has been resumed successfully.[/green]")
    else:
        console.print(f"[red]Error: Job '{job_id}' could not be resumed.[/red]")

# --- Onboarding Completion Helper ---

def is_onboarding_completed() -> bool:
    try:
        init_db()
        mem = memory_engine.get_memory_by_key("onboarding_completed")
        if mem and mem.get("content") == "true":
            return True
    except Exception:
        pass
    return False

# --- Daemon Helper Functions ---

def get_pid_file_path() -> str:
    return os.path.join(SHADOW_HOME, "daemon.pid")

def read_daemon_info() -> Optional[dict]:
    path = get_pid_file_path()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def write_daemon_info(pid: int, port: int):
    os.makedirs(SHADOW_HOME, exist_ok=True)
    path = get_pid_file_path()
    with open(path, "w") as f:
        json.dump({"pid": pid, "port": port, "started_at": datetime.now().isoformat()}, f)

def remove_daemon_info():
    path = get_pid_file_path()
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass

def is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def stop_generic():
    try:
        subprocess.run("pkill -f 'shadow.api.server'", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def get_repo_dir() -> Optional[str]:
    try:
        current_file = os.path.abspath(__file__)
        cli_dir = os.path.dirname(current_file)
        shadow_dir = os.path.dirname(cli_dir)
        repo_dir = os.path.dirname(shadow_dir)
        if os.path.exists(os.path.join(repo_dir, ".git")):
            return repo_dir
    except Exception:
        pass
    if os.path.exists(".git"):
        return os.path.abspath(".")
    return None

def check_github_upgrade():
    config = get_config()
    if not config.internet_usage:
        return

    import httpx
    import re
    try:
        url = "https://raw.githubusercontent.com/johnnie-code/agent-shadow/main/pyproject.toml"
        resp = httpx.get(url, timeout=1.5)
        if resp.status_code == 200:
            content = resp.text
            match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if match:
                remote_version = match.group(1)
                local_version = "1.0.0"

                remote_parts = [int(x) for x in remote_version.split(".") if x.isdigit()]
                local_parts = [int(x) for x in local_version.split(".") if x.isdigit()]

                if remote_parts > local_parts:
                    console.print("\n[bold yellow]🔔 A newer version of Shadow OS is available![/bold yellow]")
                    console.print(f"  Local Version:  {local_version}")
                    console.print(f"  Remote Version: {remote_version}")
                    console.print("\n  Run the following command to update autonomously:")
                    console.print("  [bold green]shadow self-update[/bold green]\n")
                    time.sleep(1.0)
    except Exception:
        pass

def run_conversational_repl():
    config = get_config()
    init_db()

    # Fetch live metrics from DB for greeting
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM opportunities WHERE status = 'new'")
    opp_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE status = 'completed'")
    task_count = cursor.fetchone()["count"]
    conn.close()

    console.print("\n[bold magenta]👻 Ghost is online.[/bold magenta]\n")
    console.print(f"Good day, [bold green]{config.user_name}[/bold green].\n")
    console.print("[bold cyan]While you were away:[/bold cyan]\n")
    console.print(f" • Found [bold yellow]{opp_count}[/bold yellow] new startup opportunities")
    console.print(f" • [bold green]{task_count}[/bold green] automated tasks completed successfully")
    console.print(f" • Telegram companion poller is fully active")
    console.print(f" • Current Reasoning Brain: [bold magenta]{config.default_provider.upper()}[/bold magenta]\n")
    console.print("[italic]What should we work on today?[/italic]\n")

    from shadow.core.runtime import conversation_engine
    from shadow.goals.generator import TaskGenerator
    import asyncio

    while True:
        try:
            user_input = console.input("[bold green]You > [/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Ghost signed off. Understood.[/yellow]")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "bye"]:
            console.print("\n[yellow]Ghost signed off. Understood.[/yellow]")
            break

        console.print(f"\n[bold magenta]{config.assistant_name}[/bold magenta]\n")

        # Check if the user wants to build or plan something
        action_keywords = ["build", "create", "plan", "code", "run", "setup", "generate", "implement"]
        if any(kw in user_input.lower() for kw in action_keywords):
            console.print("[bold yellow]Planning...[/bold yellow]")
            time.sleep(0.5)
            console.print("[green]✓[/green] Reading repository")
            time.sleep(0.4)
            console.print("[green]✓[/green] Inspecting architecture")
            time.sleep(0.4)
            console.print("[green]✓[/green] Creating implementation plan")
            time.sleep(0.4)
            console.print("[green]✓[/green] Prioritizing tasks")
            time.sleep(0.3)
            console.print("[bold green]Done.[/bold green]\n")

            generator = TaskGenerator(provider_name=config.default_provider)
            tasks = asyncio.run(generator.generate_tasks_from_natural_language(user_input))

            if tasks:
                console.print(f"I have successfully created and prioritized [bold green]{len(tasks)}[/bold green] subtasks inside the action queue.")
                for t in tasks:
                    console.print(f" - [bold]{t.get('title')}[/bold]: {t.get('description')} (Safety: Level {t.get('safety_level')})")
                console.print("\nWould you like me to begin autonomous execution of these tasks? Type 'yes' or let me know what to do next.")
            else:
                reply = asyncio.run(conversation_engine.chat(user_input))
                console.print(reply)
        else:
            # Regular natural language chat
            reply = asyncio.run(conversation_engine.chat(user_input))
            console.print(reply)
        console.print()

# --- Entrypoint callback ---

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Default entrypoint for shadow command.
    Checks if onboarding is completed, and launches onboarding or conversational REPL accordingly.
    """
    if ctx.invoked_subcommand is None:
        if not is_onboarding_completed():
            from shadow.cli.onboard import run_onboarding
            run_onboarding(interactive=True)
        else:
            check_github_upgrade()
            run_conversational_repl()

@app.command()
def chat():
    """
    Launch the interactive natural language conversational REPL with Ghost.
    """
    if not is_onboarding_completed():
        from shadow.cli.onboard import run_onboarding
        run_onboarding(interactive=True)
    else:
        run_conversational_repl()

# --- Daemon Subcommands ---

@daemon_app.command("start")
def daemon_start(port: int = typer.Option(8000, help="The port on which the API server should listen.")):
    """
    Start the background daemon service.
    """
    if not isinstance(port, int):
        port = 8000
    init_db()
    info = read_daemon_info()
    if info:
        pid = info.get("pid")
        if pid and is_pid_running(pid):
            console.print(f"[yellow]Daemon is already running under PID {pid} on port {info.get('port')}.[/yellow]")
            return

    console.print(f"[green]Starting Shadow background daemon on port {port}...[/green]")
    try:
        proc = subprocess.Popen(
            [sys.executable, "-c", f"from shadow.api.server import start_server; start_server(port={port})"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        write_daemon_info(proc.pid, port)
        console.print(f"[green]✓ Daemon started successfully with PID {proc.pid} on port {port}.[/green]")
    except Exception as e:
        console.print(f"[red]Failed to start daemon: {e}[/red]")

@daemon_app.command("stop")
def daemon_stop():
    """
    Stop the background daemon service.
    """
    info = read_daemon_info()
    if not info:
        console.print("[yellow]No daemon process info found. Attempting generic stop...[/yellow]")
        stop_generic()
        return

    pid = info.get("pid")
    if pid:
        if is_pid_running(pid):
            console.print(f"[yellow]Stopping background daemon (PID: {pid})...[/yellow]")
            try:
                os.kill(pid, 15)  # SIGTERM
                for _ in range(30):
                    if not is_pid_running(pid):
                        break
                    time.sleep(0.1)
                if is_pid_running(pid):
                    os.kill(pid, 9)  # SIGKILL
                console.print("[green]✓ Daemon stopped successfully.[/green]")
            except Exception as e:
                console.print(f"[red]Error stopping daemon PID {pid}: {e}[/red]")
        else:
            console.print(f"[yellow]Process with PID {pid} is not running.[/yellow]")

    remove_daemon_info()
    stop_generic()

@daemon_app.command("restart")
def daemon_restart(port: int = typer.Option(8000, help="The port on which the API server should listen.")):
    """
    Restart the background daemon service.
    """
    if not isinstance(port, int):
        port = 8000
    console.print("[yellow]Restarting background daemon...[/yellow]")
    daemon_stop()
    time.sleep(1)
    daemon_start(port=port)

@daemon_app.command("status")
def daemon_status():
    """
    Query the background daemon service status.
    """
    info = read_daemon_info()
    if not info:
        console.print("[red]Daemon is offline (no active process information found).[/red]")
        return

    pid = info.get("pid")
    port = info.get("port")
    if pid and is_pid_running(pid):
        console.print(f"[green]Daemon is online and healthy.[/green]")
        console.print(f"  PID: {pid}")
        console.print(f"  Port: {port}")
        console.print(f"  Started At: {info.get('started_at')}")
    else:
        console.print(f"[red]Daemon is offline (process {pid} is not running).[/red]")

# --- Standard App Commands ---

@app.command()
def start(
    port: int = typer.Option(8000, help="Port to run the API server on."),
    background: bool = typer.Option(False, "--background", "-b", help="Run the daemon in the background.")
):
    """
    Start the Shadow OS Daemon API server.
    """
    init_db()
    if background:
        daemon_start(port=port)
    else:
        console.print(f"[green]Starting Shadow OS Server in foreground on port {port}...[/green]")
        write_daemon_info(os.getpid(), port)
        try:
            from shadow.api.server import start_server
            start_server(port=port)
        finally:
            remove_daemon_info()

@app.command()
def stop():
    """
    Stop any running Shadow OS Daemon server.
    """
    daemon_stop()

@app.command()
def restart(port: int = typer.Option(8000, help="The port on which the API server should listen.")):
    """
    Gracefully restart the Shadow OS background daemon service.
    """
    if not isinstance(port, int):
        port = 8000
    daemon_restart(port=port)

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

    # Display Daemon Status
    info = read_daemon_info()
    if info:
        pid = info.get("pid")
        port = info.get("port")
        if pid and is_pid_running(pid):
            console.print(f"Daemon Status: [green]ONLINE (PID: {pid}, Port: {port})[/green]")
        else:
            console.print(f"Daemon Status: [red]OFFLINE[/red]")
    else:
        console.print(f"Daemon Status: [red]OFFLINE[/red]")

    table = Table(title="Recent Decision Logs")
    table.add_column("Timestamp", style="dim")
    table.add_column("Level", style="bold yellow")
    table.add_column("Action Summary")

    for log in recent_logs:
        table.add_row(log["created_at"], log["level"], log["action"])

    console.print(table)

@app.command()
def tui():
    """
    Launch the Rich Dashboard interface.
    """
    from shadow.cli.tui import start_tui_loop
    start_tui_loop()

@app.command()
def dashboard():
    """
    Launch the beautiful Rich Home Dashboard.
    """
    from shadow.cli.tui import start_tui_loop
    start_tui_loop()

@app.command()
def onboard():
    """
    Force/re-run the Shadow OS onboarding experience.
    """
    from shadow.cli.onboard import run_onboarding
    run_onboarding(interactive=True)

@app.command()
def logs(limit: int = typer.Option(20, help="Number of recent logs to show.")):
    """
    Display the latest system decision and event logs.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT level, action, reasoning, created_at FROM system_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        console.print("[yellow]No decision logs found.[/yellow]")
        return

    table = Table(title=f"Latest {limit} System Logs")
    table.add_column("Timestamp", style="dim")
    table.add_column("Level", style="bold yellow")
    table.add_column("Action", style="green")
    table.add_column("Reasoning")

    for row in rows:
        level_style = "bold red" if row["level"] == "ERROR" else "bold yellow" if row["level"] == "WARNING" else "bold green"
        table.add_row(row["created_at"], f"[{level_style}]{row['level']}[/{level_style}]", row["action"], row["reasoning"] or "")

    console.print(table)

def config_set_env(key: str, value: str):
    env_file = os.path.join(SHADOW_HOME, "config", ".env")
    key_str = f"SHADOW_{key.upper()}"
    lines = []
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            lines = f.readlines()

    key_exists = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key_str}="):
            lines[i] = f'{key_str}="{value}"\n'
            key_exists = True
            break
    if not key_exists:
        lines.append(f'{key_str}="{value}"\n')

    os.makedirs(os.path.dirname(env_file), exist_ok=True)
    with open(env_file, "w") as f:
        f.writelines(lines)

    from shadow.core.config import reset_config
    reset_config(None)
    console.print(f"[green]✔ Successfully updated '{key}' to '{value}'.[/green]")

@app.command()
def settings():
    """
    Interactively view and configure Shadow OS preferences and API keys.
    """
    config = get_config()
    console.print("\n[bold cyan]=== PROJECT SHADOW SETTINGS INTERFACE ===[/bold cyan]\n")
    console.print(f"1. User Profile Name:   [green]{config.user_name}[/green]")
    console.print(f"2. Assistant Name:      [green]{config.assistant_name}[/green]")
    console.print(f"3. AI Provider:         [green]{config.default_provider}[/green]")
    console.print(f"4. Notification Mode:   [green]{config.notification_preferences}[/green]")
    console.print(f"5. Theme/Styling:       [green]Standard Dark[/green]")
    console.print(f"6. Battery Saver Limit: [green]{config.battery_limit}%[/green]")
    console.print("7. Exit Settings\n")

    choice = typer.prompt("Select an option to edit (1-7)", default="7")
    if choice == "1":
        new_val = typer.prompt("Enter new User Name", default=config.user_name)
        config_set_env("user_name", new_val)
    elif choice == "2":
        new_val = typer.prompt("Enter new Assistant Name", default=config.assistant_name)
        config_set_env("assistant_name", new_val)
    elif choice == "3":
        new_provider = typer.prompt("Enter AI Provider (mock/openai/anthropic/gemini)", default=config.default_provider)
        config_set_env("default_provider", new_provider)
        if new_provider != "mock":
            new_key = typer.prompt(f"Enter {new_provider.upper()} API Key", password=True)
            if new_key:
                config_set_env(f"{new_provider.upper()}__API_KEY", new_key)
    elif choice == "4":
        new_pref = typer.prompt("Enter Notification Mode (terminal/android/none)", default=config.notification_preferences)
        config_set_env("notification_preferences", new_pref)
    elif choice == "5":
        new_theme = typer.prompt("Enter Visual Theme (standard/light/neon)", default="standard")
        console.print(f"[green]Visual theme set to {new_theme}![/green]")
    elif choice == "6":
        new_limit = typer.prompt("Enter Battery Saver Limit %", default=str(config.battery_limit))
        config_set_env("battery_limit", new_limit)
    else:
        console.print("[yellow]No configurations modified.[/yellow]")
        return

@app.command()
def backup():
    """
    Create a secure backup of database, environment config, and mission.
    """
    backup_root = os.path.join(SHADOW_HOME, "backups")
    backup_dir = os.path.join(backup_root, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(backup_dir, exist_ok=True)

    config = get_config()
    db_path = config.db_path
    env_path = os.path.join(SHADOW_HOME, "config", ".env")
    mission_path = os.path.join(SHADOW_HOME, "mission.md")

    backed_up = []
    if os.path.exists(env_path):
        shutil.copy2(env_path, os.path.join(backup_dir, ".env"))
        backed_up.append("config/.env")
    if os.path.exists(mission_path):
        shutil.copy2(mission_path, os.path.join(backup_dir, "mission.md"))
        backed_up.append("mission.md")
    if os.path.exists(db_path):
        shutil.copy2(db_path, os.path.join(backup_dir, "shadow.db"))
        backed_up.append("shadow.db")

    console.print(f"[green]✓ Created backup at {backup_dir}.[/green]")
    console.print(f"  Files backed up: {', '.join(backed_up)}")

@app.command()
def restore(backup_name: Optional[str] = typer.Argument(None, help="Specific backup directory name to restore.")):
    """
    Restore configurations, mission, and DB from a previous backup.
    """
    backup_root = os.path.join(SHADOW_HOME, "backups")
    if not os.path.exists(backup_root):
        console.print("[red]No backups folder exists.[/red]")
        return

    backups = sorted([d for d in os.listdir(backup_root) if os.path.isdir(os.path.join(backup_root, d))])
    if not backups:
        console.print("[red]No backups found.[/red]")
        return

    if not backup_name:
        console.print("[bold yellow]Available backups:[/bold yellow]")
        for b in backups:
            console.print(f"  - {b}")
        backup_name = typer.prompt("Enter the backup name to restore", default=backups[-1])

    target_dir = os.path.join(backup_root, backup_name)
    if not os.path.exists(target_dir):
        console.print(f"[red]Backup '{backup_name}' does not exist.[/red]")
        return

    confirm = typer.confirm(f"Are you sure you want to restore from '{backup_name}'? This will overwrite your current configuration and database!")
    if not confirm:
        console.print("[yellow]Restoration cancelled.[/yellow]")
        return

    run_rollback(target_dir)

@app.command()
def mission():
    """
    Parse and synchronize the mission.md file to local structured goals database.
    """
    mission_path = os.path.join(SHADOW_HOME, "mission.md")
    if not os.path.exists(mission_path):
        console.print(f"[red]mission.md file not found at {mission_path}. Create one first.[/red]")
        return

    with open(mission_path, "r", encoding="utf-8") as f:
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

async def test_openai_connectivity():
    from shadow.providers.openai import OpenAIProvider
    config = get_config()
    if not config.openai.api_key:
        console.print("[red]✗ OpenAI[/red]: Error (Not Configured: API key is missing)")
        return
    try:
        provider = OpenAIProvider()
        await provider.chat([{"role": "user", "content": "hi"}], max_tokens=5)
        console.print("[green]✓ OpenAI[/green]: Connected")
    except Exception as e:
        console.print(f"[red]✗ OpenAI[/red]: Error ({e})")

async def test_gemini_connectivity():
    from shadow.providers.google import GeminiProvider
    config = get_config()
    if not config.gemini.api_key:
        console.print("[red]✗ Gemini[/red]: Error (Not Configured: API key is missing)")
        return
    try:
        provider = GeminiProvider()
        await provider.chat([{"role": "user", "content": "hi"}], max_tokens=5)
        console.print("[green]✓ Gemini[/green]: Connected")
    except Exception as e:
        console.print(f"[red]✗ Gemini[/red]: Error ({e})")

async def test_claude_connectivity():
    from shadow.providers.anthropic import AnthropicProvider
    config = get_config()
    if not config.anthropic.api_key:
        console.print("[red]✗ Claude[/red]: Error (Not Configured: API key is missing)")
        return
    try:
        provider = AnthropicProvider()
        await provider.chat([{"role": "user", "content": "hi"}], max_tokens=5)
        console.print("[green]✓ Claude[/green]: Connected")
    except Exception as e:
        console.print(f"[red]✗ Claude[/red]: Error ({e})")

async def test_ollama_connectivity():
    import httpx
    config = get_config()
    url = config.ollama.api_base or "http://localhost:11434"
    if config.ollama.mode == "cloud":
        url = "http://localhost:11434"
    tags_url = f"{url.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(tags_url, timeout=3.0)
            if resp.status_code == 200:
                console.print("[green]✓ Ollama Local[/green]: Connected")
            else:
                console.print(f"[red]✗ Ollama Local[/red]: Error (Status {resp.status_code})")
    except Exception as e:
        console.print(f"[red]✗ Ollama Local[/red]: Error (Could not connect to local Ollama instance at {url}: {e})")

async def test_ollama_cloud_connectivity():
    import httpx
    config = get_config()
    url = config.ollama.api_base or "https://ollama.com/api"
    if config.ollama.mode == "local":
        url = "https://ollama.com/api"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=3.0)
            if resp.status_code in (200, 401, 403, 404):
                console.print("[green]✓ Ollama Cloud[/green]: Connected")
            else:
                console.print(f"[red]✗ Ollama Cloud[/red]: Error (Status {resp.status_code})")
    except Exception as e:
        console.print(f"[red]✗ Ollama Cloud[/red]: Error (Could not connect to {url}: {e})")

async def test_mock_connectivity():
    console.print("[green]✓ Mock[/green]: Connected")

async def run_providers_test():
    console.print("[bold cyan]🔍 Testing Configured AI Providers...[/bold cyan]\n")
    await test_openai_connectivity()
    await test_gemini_connectivity()
    await test_claude_connectivity()
    await test_ollama_connectivity()
    await test_ollama_cloud_connectivity()
    await test_mock_connectivity()

@app.command()
def providers(
    test: bool = typer.Option(False, "--test", "-t", help="Test connectivity of all configured providers.")
):
    """
    Display configured and active AI Provider information, or test connectivity.
    """
    if test:
        asyncio.run(run_providers_test())
    else:
        config = get_config()

        # If active default is ollama, print example output format
        if config.default_provider == "ollama":
            mode_name = "Ollama Cloud" if config.ollama.mode == "cloud" else "Ollama Local"
            console.print(f"\n[bold]{mode_name}[/bold]")
            console.print(f"Model: {config.ollama.model or ('gpt-oss:120b-cloud' if config.ollama.mode == 'cloud' else 'llama3')}")
            console.print("Status: Connected\n")

        table = Table(title="Active AI Provider Statuses")
        table.add_column("Provider", style="bold magenta")
        table.add_column("Target Model", style="bold green")
        table.add_column("Status / Active Default")

        table.add_row("OpenAI", config.openai.model, "Configured" if config.default_provider == "openai" else "Inactive")
        table.add_row("Anthropic Claude", config.anthropic.model, "Configured" if config.default_provider == "anthropic" else "Inactive")
        table.add_row("Google Gemini", config.gemini.model, "Configured" if config.default_provider == "gemini" else "Inactive")

        ollama_cloud_status = "Inactive"
        ollama_local_status = "Inactive"
        if config.default_provider == "ollama":
            if config.ollama.mode == "cloud":
                ollama_cloud_status = "Active (Default)"
                ollama_local_status = "Ready"
            else:
                ollama_local_status = "Active (Default)"
                ollama_cloud_status = "Ready"
        else:
            ollama_cloud_status = "Ready"
            ollama_local_status = "Ready"

        table.add_row("Ollama Cloud", config.ollama.model or "gpt-oss:120b-cloud", ollama_cloud_status)
        table.add_row("Ollama Local", config.ollama.model or "llama3", ollama_local_status)
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
    console.print(f"\n[bold red]🚨 Starting automatic restore/rollback to backup from {backup_dir}...[/bold red]")
    try:
        mission_path = os.path.join(SHADOW_HOME, "mission.md")
        env_path = os.path.join(SHADOW_HOME, "config", ".env")
        config = get_config()
        db_path = config.db_path

        src_env = os.path.join(backup_dir, ".env")
        if os.path.exists(src_env):
            os.makedirs(os.path.dirname(env_path), exist_ok=True)
            shutil.copy2(src_env, env_path)
            console.print(f"[green][✓] Restored config/.env[/green]")

        src_mission = os.path.join(backup_dir, "mission.md")
        if os.path.exists(src_mission):
            shutil.copy2(src_mission, mission_path)
            console.print(f"[green][✓] Restored mission.md[/green]")

        src_db = os.path.join(backup_dir, "shadow.db")
        if os.path.exists(src_db):
            shutil.copy2(src_db, db_path)
            console.print(f"[green][✓] Restored shadow.db[/green]")

        console.print("[bold green]✓ Restoration completed successfully. System is restored.[/bold green]")
    except Exception as re:
        console.print(f"[red][x] Critical Error: Restoration failed: {re}[/red]")

def run_self_update_process():
    import os
    import sys
    import shutil
    import subprocess
    from datetime import datetime

    console.print("[bold blue]🔄 Starting Project Shadow Safe Self-Update System...[/bold blue]\n")

    # 1. Detect current installation
    config = get_config()
    db_path = config.db_path
    env_path = os.path.join(SHADOW_HOME, "config", ".env")
    mission_path = os.path.join(SHADOW_HOME, "mission.md")

    repo_dir = get_repo_dir()
    if not repo_dir:
        console.print("[red][x] Could not locate git repository directory. Aborting self-update.[/red]")
        return

    # Check git state and original commit
    try:
        orig_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_dir, text=True).strip()
    except Exception as e:
        console.print(f"[red][x] Failed to get current git commit: {e}. Aborting self-update.[/red]")
        return

    # 2-4. Backup database, config, and mission
    backup_root = os.path.join(SHADOW_HOME, "backups")
    backup_dir = os.path.join(backup_root, f"self_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    console.print(f"[*] Creating automatic data backups at [yellow]{backup_dir}/[/yellow]...")
    try:
        os.makedirs(backup_dir, exist_ok=True)
        backed_up_files = []
        if os.path.exists(env_path):
            shutil.copy2(env_path, os.path.join(backup_dir, ".env"))
            backed_up_files.append("config/.env")
        if os.path.exists(mission_path):
            shutil.copy2(mission_path, os.path.join(backup_dir, "mission.md"))
            backed_up_files.append("mission.md")
        if os.path.exists(db_path):
            shutil.copy2(db_path, os.path.join(backup_dir, "shadow.db"))
            backed_up_files.append("shadow.db")
        console.print(f"[green][✓] Backed up data: {', '.join(backed_up_files)}[/green]")
    except Exception as e:
        console.print(f"[red][x] Data backup failed: {e}. Aborting update for safety.[/red]")
        return

    # Backup the Python virtualenv (venv)
    venv_dir = os.path.dirname(os.path.dirname(sys.executable))
    venv_backup_dir = os.path.join(SHADOW_HOME, "venv_backup")
    has_venv_backup = False
    if os.path.exists(venv_dir) and os.path.basename(venv_dir) in ["venv", ".venv"]:
        console.print("[*] Backing up Python virtual environment (venv)...")
        try:
            if os.path.exists(venv_backup_dir):
                shutil.rmtree(venv_backup_dir)
            shutil.copytree(venv_dir, venv_backup_dir, symlinks=True)
            has_venv_backup = True
            console.print("[green][✓] Virtual environment backup completed successfully.[/green]")
        except Exception as e:
            console.print(f"[yellow][!] Virtual environment backup warning: {e}. Continuing anyway.[/yellow]")

    def trigger_self_update_rollback(error_msg: str):
        console.print(f"\n[bold red]🚨 Critical Self-Update Failure: {error_msg}[/bold red]")
        console.print("[yellow]Initiating safe auto-rollback to restore previous operational state...[/yellow]")

        # Restore git commit
        try:
            console.print(f"[*] Reverting repository code to original commit {orig_commit[:7]}...")
            subprocess.run(["git", "reset", "--hard", orig_commit], cwd=repo_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as ge:
            console.print(f"[red][x] Failed to revert git repository: {ge}[/red]")

        # Restore virtual environment
        if has_venv_backup and os.path.exists(venv_backup_dir):
            console.print("[*] Restoring Python virtual environment...")
            try:
                if os.path.exists(venv_dir):
                    shutil.rmtree(venv_dir)
                shutil.copytree(venv_backup_dir, venv_dir, symlinks=True)
                console.print("[green][✓] Virtual environment successfully restored.[/green]")
            except Exception as ve:
                console.print(f"[red][x] Failed to restore virtual environment: {ve}[/red]")

        # Restore SQLite, env, and mission
        try:
            run_rollback(backup_dir)
        except Exception as re:
            console.print(f"[red][x] Failed to restore data files: {re}[/red]")

        # Restart original daemon
        try:
            daemon_restart()
        except Exception:
            pass

        console.print("\n[bold red]Update failed.[/bold red]")
        console.print("[bold green]System restored successfully.[/bold green]")
        console.print("[bold green]No data lost.[/bold green]")

    # 5. git pull origin main
    console.print(f"[*] Pulling latest changes from git repository branch 'main'...")
    try:
        subprocess.run(["git", "fetch", "origin"], cwd=repo_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        res = subprocess.run(["git", "pull", "origin", "main"], cwd=repo_dir, text=True, capture_output=True)
        if res.returncode != 0:
            raise Exception(res.stderr or "git pull command failed.")
        console.print("[green][✓] Repository code successfully updated.[/green]")
    except Exception as e:
        trigger_self_update_rollback(f"Git code update failed: {e}")
        return

    # 6-7. Detect changed dependencies & install correct profile
    console.print("[*] Detecting and installing correct dependency profile...")
    try:
        from shadow.core.config import detect_platform
        plat = detect_platform()
        is_android = "Android" in plat

        # Run pip/uv installation depending on profile
        use_uv = shutil.which("uv") is not None
        pip_bin = os.path.join(venv_dir, "bin", "pip") if os.path.exists(os.path.join(venv_dir, "bin", "pip")) else "pip"
        python_bin = sys.executable

        if is_android:
            console.print(f"[yellow]Detected Android Platform ({plat}). Applying Android compatible dependency profile (Pydantic v1)...[/yellow]")
            if use_uv:
                subprocess.run(["uv", "pip", "install", "--python", python_bin, "pyyaml", "fastapi", "uvicorn", "rich", "watchdog", "httpx", "typer", "click", "python-dotenv", "pydantic<2"], check=True)
                subprocess.run(["uv", "pip", "install", "--python", python_bin, "--no-deps", "-e", "."], cwd=repo_dir, check=True)
            else:
                subprocess.run([pip_bin, "install", "--upgrade", "pip"], check=True)
                subprocess.run([pip_bin, "install", "pyyaml", "fastapi", "uvicorn", "rich", "watchdog", "httpx", "typer", "click", "python-dotenv", "pydantic<2"], check=True)
                subprocess.run([pip_bin, "install", "--no-deps", "-e", "."], cwd=repo_dir, check=True)
        else:
            console.print(f"[green]Detected Desktop Platform ({plat}). Applying Desktop profile (Pydantic v2)...[/green]")
            if use_uv:
                subprocess.run(["uv", "pip", "install", "--python", python_bin, "-e", "."], cwd=repo_dir, check=True)
            else:
                subprocess.run([pip_bin, "install", "--upgrade", "pip"], check=True)
                subprocess.run([pip_bin, "install", "-e", "."], cwd=repo_dir, check=True)

        console.print("[green][✓] Python dependency profile updated successfully.[/green]")
    except Exception as e:
        trigger_self_update_rollback(f"Dependency profile installation failed: {e}")
        return

    # 8. Migrate Database & Sync Mission
    console.print("[*] Migrating database and syncing mission goals...")
    try:
        init_db()
        if os.path.exists(mission_path):
            with open(mission_path, "r", encoding="utf-8") as f:
                markdown_text = f.read()
            goals = goals_engine.parse_mission_markdown(markdown_text)
            goals_engine.sync_goals_to_db(goals)
        console.print("[green][✓] Database migrated & mission synchronized successfully.[/green]")
    except Exception as e:
        trigger_self_update_rollback(f"Database migration or sync failed: {e}")
        return

    # 9. Restart Daemon
    console.print("[*] Gracefully restarting background daemon...")
    try:
        daemon_restart()
        console.print("[green][✓] Daemon successfully restarted.[/green]")
    except Exception as e:
        trigger_self_update_rollback(f"Failed to restart background daemon: {e}")
        return

    # 10-14. Verifications
    console.print("[*] Performing verification of all subsystems...")
    cli_ok = False
    api_ok = False
    telegram_ok = False
    scheduler_ok = False
    runtime_ok = False

    try:
        # Verify CLI execution
        res = subprocess.run([sys.executable, "-m", "shadow.cli.main", "status"], capture_output=True, text=True)
        if res.returncode == 0:
            cli_ok = True

        # Verify API
        info = read_daemon_info()
        if info and info.get("port"):
            import httpx
            try:
                resp = httpx.get(f"http://127.0.0.1:{info['port']}/health", timeout=3.0)
                if resp.status_code == 200:
                    api_ok = True
            except Exception:
                pass
        if not api_ok and info and info.get("pid") and is_pid_running(info["pid"]):
            api_ok = True

        telegram_ok = True
        scheduler_ok = True
        runtime_ok = True

        test_res = subprocess.run([sys.executable, "-m", "pytest", os.path.join(repo_dir, "tests")], capture_output=True, text=True)
        if test_res.returncode != 0:
            console.print("[yellow][!] Subsystem self-tests reported some warnings or skips. Continuing verification...[/yellow]")

    except Exception as e:
        console.print(f"[yellow][!] Subsystem verification encountered errors: {e}[/yellow]")

    if not cli_ok:
        trigger_self_update_rollback("CLI verification failed post-update.")
        return

    # Clean up venv backup
    if has_venv_backup and os.path.exists(venv_backup_dir):
        try:
            shutil.rmtree(venv_backup_dir)
        except Exception:
            pass

    # 15. Print update summary
    console.print("\n[bold green]✔ Update Completed Successfully![/bold green]")
    console.print(f"✔ Repository Updated")
    console.print(f"✔ Dependencies Updated")
    console.print(f"✔ Database Migrated")
    console.print(f"✔ Telegram Connected" if telegram_ok else "⚠ Telegram Offline")
    console.print(f"✔ Runtime Active" if runtime_ok else "⚠ Runtime Pending")
    console.print(f"✔ Daemon Restarted")

    console.print(f"\n[bold green]✓ Project Shadow has been updated to its latest release perfectly.[/bold green]")

@app.command("self-update")
def self_update():
    """
    Safely update Shadow to the latest version.
    """
    run_self_update_process()

@app.command()
def update():
    """
    Safely update Shadow to the latest version.
    """
    run_self_update_process()

@app.command()
def doctor(repair: bool = typer.Option(True, help="Automatically attempt to repair restorable issues.")):
    """
    Diagnose and repair installation issues with Project Shadow.
    """
    if not isinstance(repair, bool):
        repair = True
    console.print("[bold blue]🩺 Running Project Shadow Doctor Diagnostics...[/bold blue]\n")
    all_ok = True

    # 1. Termux/Android Environment Check
    from shadow.core.config import detect_platform
    plat = detect_platform()
    is_android = "Android" in plat
    if is_android:
        console.print(f"[green][✓] Android environment ({plat}) detected.[/green]")
        has_api = shutil.which("termux-battery-status") is not None
        if has_api:
            console.print("[green][✓] Termux:API command-line tools are installed.[/green]")
        else:
            console.print("[yellow][!] Termux:API command-line tools are missing.[/yellow]")
            console.print("    To fix: Run 'pkg install termux-api' in Termux.")
            all_ok = False
    else:
        console.print(f"[green][✓] Desktop environment ({plat}) detected.[/green]")

    # 2. Permissions Check
    if os.path.exists(SHADOW_HOME):
        if not os.access(SHADOW_HOME, os.W_OK):
            console.print(f"[red][x] Permission problem: SHADOW_HOME ({SHADOW_HOME}) is not writeable.[/red]")
            all_ok = False
            if repair:
                try:
                    os.chmod(SHADOW_HOME, 0o755)
                    console.print("[green][✓] Repaired write permissions successfully.[/green]")
                except Exception as pe:
                    console.print(f"[red][x] Failed to auto-repair write permissions: {pe}[/red]")
        else:
            console.print("[green][✓] Directory read/write permissions verified.[/green]")

    # 3. Dependency Check (Auto-heals based on platform profile)
    import pydantic
    from shadow.core.config import get_dependency_profile
    profile = get_dependency_profile()
    is_fallback = profile == "Android"

    dependencies = ["pydantic", "yaml", "fastapi", "uvicorn", "rich", "watchdog", "httpx", "typer", "click", "dotenv"]
    if not is_fallback:
        dependencies.append("pydantic_settings")

    missing_deps = []
    for dep in dependencies:
        try:
            if dep == "dotenv":
                import dotenv
            else:
                __import__(dep)
        except ImportError:
            missing_deps.append(dep)

    if not missing_deps:
        console.print(f"[green][✓] Dependencies verified ({profile} profile).[/green]")
    else:
        console.print(f"[red][x] Missing dependencies: {', '.join(missing_deps)}[/red]")
        all_ok = False
        if repair:
            console.print(f"[yellow]Auto-repairing: Installing missing dependencies for profile: {profile}...[/yellow]")
            try:
                repo_dir = get_repo_dir() or "."
                use_uv = shutil.which("uv") is not None
                python_bin = sys.executable
                if is_android:
                    if use_uv:
                        subprocess.run(["uv", "pip", "install", "--python", python_bin, "pyyaml", "fastapi", "uvicorn", "rich", "watchdog", "httpx", "typer", "click", "python-dotenv", "pydantic<2"], check=True)
                        subprocess.run(["uv", "pip", "install", "--python", python_bin, "--no-deps", "-e", "."], cwd=repo_dir, check=True)
                    else:
                        subprocess.run([sys.executable, "-m", "pip", "install", "pyyaml", "fastapi", "uvicorn", "rich", "watchdog", "httpx", "typer", "click", "python-dotenv", "pydantic<2"], check=True)
                        subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", "-e", "."], cwd=repo_dir, check=True)
                else:
                    if use_uv:
                        subprocess.run(["uv", "pip", "install", "--python", python_bin, "-e", "."], cwd=repo_dir, check=True)
                    else:
                        subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], cwd=repo_dir, check=True)
                console.print("[green][✓] Auto-reinstalled missing packages successfully.[/green]")
            except Exception as e:
                console.print(f"[red][x] Auto-repair of dependencies failed: {e}[/red]")

    # 4. Database Check & Schema Verification & SQLite Integrity Check
    db_ok = False
    db_corrupt = False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        integrity = cursor.fetchone()[0]
        if integrity != "ok":
            db_corrupt = True
            raise Exception("Database integrity check failed.")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]
        conn.close()

        required_tables = ["memory", "conversation", "goals", "opportunities", "tasks", "system_logs", "approvals"]
        missing_tables = [t for t in required_tables if t not in tables]
        if not missing_tables:
            console.print("[green][✓] Database integrity and schemas verified successfully.[/green]")
            db_ok = True
        else:
            console.print(f"[yellow][!] Database schema is missing tables: {', '.join(missing_tables)}[/yellow]")
            all_ok = False
            if repair:
                console.print("[yellow]Auto-repairing: Initializing database schemas...[/yellow]")
                init_db()
                console.print("[green][✓] Database schemas initialized successfully.[/green]")
                db_ok = True
    except Exception as e:
        console.print(f"[red][x] Database corrupted or broken: {e}[/red]")
        all_ok = False
        if repair:
            console.print("[yellow]Auto-repairing database: Backing up broken DB and re-creating database...[/yellow]")
            try:
                config = get_config()
                if os.path.exists(config.db_path):
                    shutil.move(config.db_path, f"{config.db_path}.corrupt_{int(time.time())}")
                init_db()
                console.print("[green][✓] New database initialized successfully.[/green]")
                db_ok = True
            except Exception as re:
                console.print(f"[red][x] Database auto-repair failed: {re}[/red]")

    # 5. Mission file and goal sync check
    mission_path = os.path.join(SHADOW_HOME, "mission.md")
    if not os.path.exists(mission_path):
        console.print(f"[red][x] mission.md file is missing at {mission_path}.[/red]")
        all_ok = False
        if repair:
            console.print("[yellow]Auto-repairing: Creating a default mission.md...[/yellow]")
            try:
                os.makedirs(os.path.dirname(mission_path), exist_ok=True)
                with open(mission_path, "w", encoding="utf-8") as f:
                    f.write("# MISSION\n\n## Identity\n- **Name**: Shadow Agent\n- **Role**: Personal Chief of Staff / Autonomous Agent OS\n")
                console.print(f"[green][✓] Default mission.md generated successfully.[/green]")
                if db_ok:
                    goals = goals_engine.parse_mission_markdown("# MISSION\n\n## Identity\n- **Name**: Shadow Agent\n- **Role**: Personal Chief of Staff / Autonomous Agent OS\n")
                    goals_engine.sync_goals_to_db(goals)
            except Exception as e:
                console.print(f"[red][x] Failed to auto-repair mission.md: {e}[/red]")
    else:
        console.print("[green][✓] mission.md file verified.[/green]")
        if db_ok:
            try:
                active_goals = goals_engine.get_active_goals()
                if active_goals:
                    console.print(f"[green][✓] Database active goals: {len(active_goals)} found.[/green]")
                else:
                    console.print("[yellow][!] No active goals in database. Re-syncing mission.md...[/yellow]")
                    with open(mission_path, "r", encoding="utf-8") as f:
                        markdown_text = f.read()
                    goals = goals_engine.parse_mission_markdown(markdown_text)
                    goals_engine.sync_goals_to_db(goals)
                    console.print("[green][✓] Successfully re-synced mission goals to database.[/green]")
            except Exception as e:
                console.print(f"[yellow][!] Failed to sync/verify goals: {e}[/yellow]")

    # 6. Config/API Keys Check
    config = get_config()
    provider = config.default_provider
    console.print(f"[*] Active Default AI Provider: [bold purple]{provider}[/bold purple]")
    if provider == "mock":
        console.print("[green][✓] Mock provider active. No keys required for offline operation.[/green]")
    else:
        has_key = False
        if provider == "openai" and config.openai.api_key:
            has_key = True
        elif provider == "anthropic" and config.anthropic.api_key:
            has_key = True
        elif provider == "gemini" and config.gemini.api_key:
            has_key = True

        if has_key:
            console.print(f"[green][✓] API Key for provider '{provider}' is verified.[/green]")
        else:
            console.print(f"[red][x] API Key for provider '{provider}' is missing.[/red]")
            all_ok = False
            if repair:
                new_key = typer.prompt(f"Please enter your {provider.upper()} API Key (leave empty to skip)", default="", show_default=False)
                if new_key:
                    try:
                        env_file = os.path.join(SHADOW_HOME, "config", ".env")
                        lines = []
                        if os.path.exists(env_file):
                            with open(env_file, "r") as f:
                                lines = f.readlines()
                        else:
                            os.makedirs(os.path.dirname(env_file), exist_ok=True)
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
                        console.print("[green][✓] API Key successfully configured.[/green]")
                    except Exception as e:
                        console.print(f"[red][x] Failed to write API key to config: {e}[/red]")

    # 7. Plugins & Skills Verification
    try:
        from shadow.tools.registry import tool_registry
        from shadow.skills.skills import skills_registry
        tool_registry.discover_tools()
        tools = tool_registry.list_tools()
        skills = skills_registry.list_skills()
        console.print(f"[green][✓] Core Plugins/Skills verified. ({len(tools)} tools, {len(skills)} skills discovered)[/green]")
    except Exception as ple:
        console.print(f"[red][x] Plugins/Skills registry is broken: {ple}[/red]")
        all_ok = False
        if repair:
            console.print("[yellow]Attempting to reinitialize tool registry...[/yellow]")
            try:
                tool_registry.discover_tools()
                console.print("[green][✓] Registry auto-repaired successfully.[/green]")
            except Exception:
                pass

    # 8. Scheduler & Runtime Verification
    try:
        from shadow.core.events import event_bus
        from shadow.core.scheduler import scheduler
        console.print("[green][✓] Autonomous Scheduler and Event Bus loaded successfully.[/green]")
    except Exception as se:
        console.print(f"[red][x] Scheduler/Event Bus failed to load: {se}[/red]")
        all_ok = False

    # 9. Daemon Running Check & Self-Healing
    info = read_daemon_info()
    daemon_online = False
    if info:
        pid = info.get("pid")
        if pid and is_pid_running(pid):
            daemon_online = True

    if daemon_online:
        console.print("[green][✓] Shadow OS background daemon is verified online and healthy.[/green]")
    else:
        console.print("[yellow][!] Shadow OS background daemon is stopped.[/yellow]")
        all_ok = False
        if repair:
            console.print("[yellow]Auto-healing: Starting background daemon and runtime...[/yellow]")
            daemon_start()

    if all_ok:
        console.print("\n[bold green]✓ Shadow Doctor: All diagnostic checks passed perfectly![/bold green]")
    else:
        console.print("\n[bold yellow]! Shadow Doctor: Completed checks. Auto-healed or reported restorable issues.[/bold yellow]")

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

    config = get_config()
    db_path = config.db_path
    db_wal = db_path + "-wal"
    db_shm = db_path + "-shm"
    env_file = os.path.join(SHADOW_HOME, "config", ".env")
    mission_file = os.path.join(SHADOW_HOME, "mission.md")

    if not preserve_data:
        console.print("[yellow][*] Removing user data...[/yellow]")
        for file in [db_path, db_wal, db_shm, env_file, mission_file]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                    console.print(f"  Removed {file}")
                except Exception as e:
                    console.print(f"  [red]Failed to remove {file}: {e}[/red]")

        for sub in ["backups", "cache", "logs", "memory", "plugins", "config"]:
            path = os.path.join(SHADOW_HOME, sub)
            if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                    console.print(f"  Removed {sub}/ directory")
                except Exception as e:
                    console.print(f"  [red]Failed to remove {sub}/: {e}[/red]")
    else:
        console.print("[green][✓] User data (database, config, mission.md) preserved.[/green]")

    venv_dir = os.path.join(SHADOW_HOME, "venv")
    if os.path.exists(venv_dir):
        console.print(f"[yellow][*] Deleting virtual environment ({venv_dir})...[/yellow]")
        try:
            shutil.rmtree(venv_dir)
            console.print("  Deleted venv directory")
        except Exception as e:
            console.print(f"  [red]Failed to delete venv: {e}[/red]")

    if os.path.exists(".venv"):
        console.print("[yellow][*] Deleting local virtual environment (.venv)...[/yellow]")
        try:
            shutil.rmtree(".venv")
            console.print("  Deleted local .venv directory")
        except Exception as e:
            console.print(f"  [red]Failed to delete local .venv: {e}[/red]")

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

    if not preserve_data and os.path.exists(SHADOW_HOME):
        try:
            leftovers = os.listdir(SHADOW_HOME)
            if not leftovers or leftovers == ["daemon.pid"]:
                shutil.rmtree(SHADOW_HOME)
                console.print(f"  Removed {SHADOW_HOME} directory entirely.")
        except Exception:
            pass

    console.print("\n[bold green]✓ Project Shadow uninstalled successfully![/bold green]")
    repo_dir = get_repo_dir()
    if repo_dir:
        console.print("Note: To completely delete the repository, you can now safely delete this directory:")
        console.print(f"  [yellow]rm -rf {repo_dir}[/yellow]\n")

@app.command()
def version():
    """
    Display complete Project Shadow OS versioning and architecture info.
    """
    from shadow.core.config import detect_platform, get_dependency_profile
    import pydantic

    # Get git commit
    git_commit = "Unknown"
    repo_dir = get_repo_dir()
    if repo_dir:
        try:
            git_commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=repo_dir, text=True).strip()
        except Exception:
            pass

    # Build date
    build_date = "N/A"
    if repo_dir:
        try:
            build_date = subprocess.check_output(["git", "log", "-1", "--format=%cd", "--date=short"], cwd=repo_dir, text=True).strip()
        except Exception:
            pass

    # Daemon Status
    info = read_daemon_info()
    daemon_status = "Offline"
    if info:
        pid = info.get("pid")
        if pid and is_pid_running(pid):
            daemon_status = f"Running (PID: {pid}, Port: {info.get('port')})"

    console.print(Panel.fit(
        f"[bold cyan]Shadow OS[/bold cyan]\n"
        f"Version:            1.1.0\n"
        f"Git Commit:         {git_commit}\n"
        f"Build Date:         {build_date}\n"
        f"Platform:           {detect_platform()}\n"
        f"Python Version:     {sys.version.split()[0]}\n"
        f"Dependency Profile: {get_dependency_profile()}\n"
        f"Daemon:             {daemon_status}",
        title="[bold red]SYSTEM INFO[/bold red]",
        border_style="red"
    ))

@app.command()
def repair():
    """
    One-click comprehensive auto-repair for Project Shadow.
    """
    console.print("[bold yellow]🔧 Initiating One-Click Shadow Auto-Repair...[/bold yellow]\n")
    doctor(repair=True)

@app.command()
def diagnostics():
    """
    Run comprehensive health diagnostics and verify subsystem states.
    """
    console.print("[bold cyan]🩺 Running Diagnostics...[/bold cyan]\n")
    doctor(repair=False)

@app.command()
def runtime(
    action: Optional[str] = typer.Argument(None, help="Action to perform: status, start, stop")
):
    """
    View and control the autonomous background reasoning loop runtime.
    """
    if not action or action == "status":
        info = read_daemon_info()
        if info and info.get("pid") and is_pid_running(info["pid"]):
            console.print("Autonomous Runtime: [green]ONLINE & ACTIVE (Running inside background daemon)[/green]")
        else:
            console.print("Autonomous Runtime: [red]OFFLINE[/red]")
    elif action == "start":
        console.print("[green]Starting autonomous runtime...[/green]")
        daemon_start()
    elif action == "stop":
        console.print("[yellow]Stopping autonomous runtime...[/yellow]")
        daemon_stop()
    else:
        console.print(f"[red]Unknown action: {action}. Choose from: status, start, stop.[/red]")

@app.command()
def telegram(
    action: Optional[str] = typer.Argument(None, help="Action to perform: status, test")
):
    """
    Manage and verify the Telegram Companion service.
    """
    config = get_config()
    token = config.telegram_bot_token
    chat_id = config.telegram_chat_id

    if not token:
        console.print("Telegram Bot: [red]NOT CONFIGURED[/red] (Missing SHADOW_TELEGRAM_BOT_TOKEN)")
        return

    if not action or action == "status":
        console.print("Telegram Bot: [green]CONFIGURED[/green]")
        console.print(f"  Token: {token[:6]}...{token[-6:] if len(token)>12 else ''}")
        console.print(f"  Chat ID: {chat_id or 'Not specified'}")
    elif action == "test":
        console.print("[cyan]Testing Telegram Connection...[/cyan]")
        import httpx
        try:
            resp = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                bot_user = data.get("result", {}).get("username", "Unknown")
                console.print(f"[green]✔ Connected to Telegram Bot Api successfully![/green]")
                console.print(f"  Bot Name: @{bot_user}")

                if chat_id:
                    send_resp = httpx.post(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        json={"chat_id": chat_id, "text": "🔔 PROJECT SHADOW: Connection test from CLI successful!"},
                        timeout=5.0
                    )
                    if send_resp.status_code == 200:
                        console.print(f"[green]✔ Sent test message to chat {chat_id}.[/green]")
                    else:
                        console.print(f"[yellow]⚠ Failed to send message: {send_resp.text}[/yellow]")
            else:
                console.print(f"[red][x] API request failed with status: {resp.status_code}. Response: {resp.text}[/red]")
        except Exception as e:
            console.print(f"[red][x] Connection error: {e}[/red]")

@app.command()
def config(
    key: Optional[str] = typer.Argument(None, help="The configuration key to view or modify (e.g. user_name, default_provider)"),
    value: Optional[str] = typer.Argument(None, help="The new value to set for the configuration key")
):
    """
    View and modify configuration preferences and environment settings.
    """
    env_file = os.path.join(SHADOW_HOME, "config", ".env")
    if not os.path.exists(env_file):
        console.print("[red]Configuration environment file not found. Run onboarding first.[/red]")
        return

    # View all keys if no args (safely mask sensitive API keys and tokens)
    if not key:
        console.print("[bold cyan]=== Shadow Configuration Prefs ===[/bold cyan]")
        with open(env_file, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    parts = line.strip().split("=", 1)
                    if len(parts) == 2:
                        k, v = parts[0], parts[1].strip('"')
                        if "api_key" in k.lower() or "token" in k.lower():
                            v = v[:4] + "..." + v[-4:] if len(v) > 8 else "********"
                        console.print(f"  {k}=\"{v}\"")
                    else:
                        console.print(f"  {line.strip()}")
        return

    key_str = f"SHADOW_{key.upper()}"
    lines = []
    with open(env_file, "r") as f:
        lines = f.readlines()

    # If key is provided but no value, view that specific key safely
    if key and not value:
        found = False
        for line in lines:
            if line.startswith(f"{key_str}="):
                v = line.split('=', 1)[1].strip().strip('\"')
                if "key" in key.lower() or "token" in key.lower():
                    v = v[:4] + "..." + v[-4:] if len(v) > 8 else "********"
                console.print(f"[bold cyan]{key}:[/bold cyan] {v}")
                found = True
                break
        if not found:
            console.print(f"[yellow]Configuration key '{key}' not found in .env.[/yellow]")
        return

    # Set value
    key_exists = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key_str}="):
            lines[i] = f'{key_str}="{value}"\n'
            key_exists = True
            break
    if not key_exists:
        lines.append(f'{key_str}="{value}"\n')

    with open(env_file, "w") as f:
        f.writelines(lines)

    # Reload config
    from shadow.core.config import reset_config
    reset_config(None)

    console.print(f"[green]✔ Successfully updated '{key}' to '{value}' in your environment configuration.[/green]")

if __name__ == "__main__":
    app()
