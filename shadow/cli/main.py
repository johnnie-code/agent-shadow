import os
import sys
import typer
import asyncio
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

@app.command()
def update():
    """
    Synchronize configuration, refresh goals, and clean database tables.
    """
    console.print("[green]Re-initializing tables and reloading config settings...[/green]")
    init_db()
    if os.path.exists("mission.md"):
        with open("mission.md", "r", encoding="utf-8") as f:
            markdown_text = f.read()
        goals = goals_engine.parse_mission_markdown(markdown_text)
        goals_engine.sync_goals_to_db(goals)
    console.print("[green]System updated successfully.[/green]")

if __name__ == "__main__":
    app()
