import os
import sys
import time
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from shadow.core.config import get_config
from shadow.core.database import get_db_connection
from shadow.goals.engine import goals_engine

console = Console()

def make_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=3)
    )
    layout["body"].split_row(
        Layout(name="left", ratio=1),
        Layout(name="right", ratio=1)
    )
    return layout

def get_header() -> Panel:
    config = get_config()
    return Panel(
        f"[bold cyan]SHADOW OS INTEGRATED DASHBOARD[/bold cyan] | Status: [bold green]ONLINE[/bold green] | Provider: [green]{config.default_provider.upper()}[/green]",
        style="bold white on blue",
        expand=True
    )

def get_footer() -> Panel:
    return Panel(
        "Ctrl+C to Exit Dashboard | [cyan]shadow start[/cyan] [dim]to boot daemon[/dim] | [magenta]shadow status[/magenta] [dim]for CLI query[/dim]",
        style="white",
        expand=True
    )

def get_left_panel() -> Table:
    table = Table(title="Mission Progress & Core Goals")
    table.add_column("Goal Title", style="bold green")
    table.add_column("Category")
    table.add_column("Priority", style="bold magenta")
    table.add_column("Status")

    active_goals = goals_engine.get_active_goals()
    for g in active_goals[:5]:
        table.add_row(g["title"][:30], g["category"], g["priority"], g["status"])

    return table

def get_status_overview() -> Panel:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Calculate queue sizes
    cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE status = 'pending'")
    pending_tasks = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE status = 'completed'")
    completed_tasks = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM memory")
    memory_blocks = cursor.fetchone()["count"]

    conn.close()

    status_text = (
        f"[bold white]System Status:[/bold white] Idle\n"
        f"[bold white]Active Agents Running:[/bold white] PlannerAgent, ResearchAgent, CodingAgent\n"
        f"[bold yellow]Pending Tasks Queue:[/bold yellow] {pending_tasks} items\n"
        f"[bold green]Completed Tasks:[/bold green] {completed_tasks} items\n"
        f"[bold cyan]Memory Block Storage:[/bold cyan] {memory_blocks} records\n"
        f"[bold magenta]Notifications Feed:[/bold magenta] Active"
    )
    return Panel(status_text, title="Active Core Metrics & States")

def get_logs_panel() -> Panel:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT level, action, created_at FROM system_logs ORDER BY id DESC LIMIT 5")
    logs = cursor.fetchall()
    conn.close()

    text = ""
    for log in logs:
        color = "red" if log["level"] == "ERROR" else "yellow" if log["level"] == "WARNING" else "green"
        text += f"[{log['created_at']}] [{color}]{log['level']}[/{color}] - {log['action'][:40]}...\n"

    return Panel(text or "No system decision logs recorded yet.", title="Dynamic Decision & Event Logs")

def get_tasks_table() -> Table:
    table = Table(title="Upcoming Actions Queue")
    table.add_column("ID", style="dim")
    table.add_column("Action Task", style="bold yellow")
    table.add_column("Score", style="cyan")
    table.add_column("Status")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, priority_score, status FROM tasks ORDER BY priority_score DESC LIMIT 4")
    tasks = cursor.fetchall()
    conn.close()

    for t in tasks:
        table.add_row(str(t["id"]), t["title"][:30], f"{t['priority_score']:.2f}", t["status"])
    return table

def start_tui_loop():
    layout = make_layout()
    layout["header"].update(get_header())
    layout["footer"].update(get_footer())

    try:
        with Live(layout, refresh_per_second=1, screen=True) as live:
            while True:
                layout["left"].update(Panel(get_left_panel(), title="Mission & Projects Tracker"))
                layout["right"].split_column(
                    Layout(get_status_overview(), size=8),
                    Layout(Panel(get_tasks_table(), title="Task Scheduler Queue")),
                    Layout(get_logs_panel())
                )
                time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard closed gracefully.[/yellow]")

if __name__ == "__main__":
    start_tui_loop()
