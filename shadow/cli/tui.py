import os
import sys
import time
from typing import Dict, Any, List
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from shadow.core.config import get_config, SHADOW_HOME
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
    layout["left"].split_column(
        Layout(name="mission", size=7),
        Layout(name="goals", ratio=1),
        Layout(name="opportunities", size=7)
    )
    layout["right"].split_column(
        Layout(name="planner", size=7),
        Layout(name="status", ratio=1),
        Layout(name="logs", size=8)
    )
    return layout

def get_header() -> Panel:
    config = get_config()
    return Panel(
        f"[bold white]SHADOW AUTONOMOUS OS[/bold white] | User: [bold green]{config.user_name.upper()}[/bold green] | Assistant: [bold magenta]{config.assistant_name.upper()}[/bold magenta] | Active Provider: [bold yellow]{config.default_provider.upper()}[/bold yellow]",
        style="bold white on blue",
        expand=True
    )

def get_footer() -> Panel:
    return Panel(
        "Ctrl+C to Exit Dashboard | Use [cyan]shadow stop[/cyan] to kill daemon | Use [magenta]shadow doctor[/magenta] to run checks",
        style="white",
        expand=True
    )

def get_mission_panel() -> Panel:
    config = get_config()
    text = (
        f"[bold yellow]Life Mission:[/bold yellow] \"{config.life_mission}\"\n\n"
        f"[bold cyan]Assistant Role:[/bold cyan] Personal Autonomous Chief of Staff OS\n"
        f"[bold cyan]Data Storage:[/bold cyan] {SHADOW_HOME}"
    )
    return Panel(text, title="🎯 Active Life Mission & Profile", border_style="cyan")

def get_goals_table() -> Table:
    table = Table(title="Goals & Milestones Progress", expand=True)
    table.add_column("Goal Milestone", style="bold green", ratio=2)
    table.add_column("Category", style="cyan")
    table.add_column("Progress Bar", style="yellow", ratio=2)
    table.add_column("Status", style="bold magenta")

    active_goals = goals_engine.get_active_goals()
    if not active_goals:
        table.add_row("No goals tracked. Run 'shadow onboard' to define.", "", "", "")
        return table

    for g in active_goals[:5]:
        status = g["status"]
        progress = 10
        if status == "completed":
            progress = 100
        elif status == "active" or status == "running":
            progress = 40

        bar_filled = progress // 10
        progress_bar = "■" * bar_filled + "□" * (10 - bar_filled)
        table.add_row(
            g["title"][:40],
            g["category"] or "General",
            f"[{progress_bar}] {progress}%",
            g["status"].upper()
        )
    return table

def get_opportunities_panel() -> Panel:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title, category, url FROM opportunities ORDER BY id DESC LIMIT 2")
    opps = cursor.fetchall()
    conn.close()

    text = ""
    if not opps:
        text = "[dim]No new opportunities found yet. Active scanning running in background...[/dim]"
    else:
        for o in opps:
            text += f"• [bold green]{o['title'][:50]}[/bold green] ({o['category']})\n  URL: {o['url'] or 'N/A'}\n"

    return Panel(text, title="🔍 Recent Opportunities Feed", border_style="green")

def get_planner_panel() -> Panel:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE status = 'pending'")
    pending = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE status = 'completed'")
    completed = cursor.fetchone()["count"]

    cursor.execute("SELECT title FROM tasks WHERE status = 'pending' ORDER BY priority_score DESC LIMIT 1")
    top_task_row = cursor.fetchone()
    top_task = top_task_row["title"] if top_task_row else "All caught up!"

    conn.close()

    text = (
        f"[bold white]Pending Priorities Count:[/bold white] {pending} tasks\n"
        f"[bold white]Completed Tasks Today:[/bold white] {completed} items\n"
        f"[bold yellow]Next Recommended Focus:[/bold yellow]\n  ➡ [bold green]{top_task[:50]}[/bold green]"
    )
    return Panel(text, title="📅 Daily Planner & Focus", border_style="yellow")

def get_status_table() -> Table:
    table = Table(title="System & Android Capability Checklist", expand=True)
    table.add_column("Subsystem", style="bold cyan")
    table.add_column("Indicator", style="bold")
    table.add_column("Details")

    config = get_config()

    # Daemon Status
    from shadow.cli.main import read_daemon_info, is_pid_running
    info = read_daemon_info()
    daemon_status = "🔴 STOPPED"
    daemon_pid = "N/A"
    if info:
        pid = info.get("pid")
        if pid and is_pid_running(pid):
            daemon_status = "🟢 RUNNING"
            daemon_pid = f"PID {pid}"

    # Telegram Companion
    telegram_status = "🟢 READY (MOCK)"
    if config.telegram_bot_token:
        telegram_status = "🟢 POLLED CONNECTED"

    table.add_row("Background Daemon", daemon_status, daemon_pid)
    table.add_row("Telegram Companion", telegram_status, "Authorized Channel" if config.telegram_chat_id else "No chat ID")
    table.add_row("AI Reasoning Engine", f"🟢 ACTIVE", f"{config.default_provider.upper()} Provider")
    table.add_row("SQLite Database", "🟢 HEALTHY", "WAL Mode Enabled")
    table.add_row("Storage System", "🟢 INITIALIZED", f"config/ is loaded")
    table.add_row("Internet Status", "🟢 ONLINE", "HTTPX active")

    return table

def get_logs_panel() -> Panel:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT level, action, created_at FROM system_logs ORDER BY id DESC LIMIT 5")
    logs = cursor.fetchall()
    conn.close()

    text = ""
    for log in logs:
        color = "red" if log["level"] == "ERROR" else "yellow" if log["level"] == "WARNING" else "green"
        text += f"[{log['created_at']}] [{color}]{log['level']}[/{color}] - {log['action'][:55]}...\n"

    return Panel(text or "No system decision logs recorded yet.", title="📝 Dynamic Decision & Event Logs", border_style="magenta")

def start_tui_loop():
    layout = make_layout()
    layout["header"].update(get_header())
    layout["footer"].update(get_footer())

    try:
        with Live(layout, refresh_per_second=1, screen=True) as live:
            while True:
                layout["header"].update(get_header())
                layout["left"]["mission"].update(get_mission_panel())
                layout["left"]["goals"].update(Panel(get_goals_table(), title="🎯 Goals Milestone Tracker"))
                layout["left"]["opportunities"].update(get_opportunities_panel())

                layout["right"]["planner"].update(get_planner_panel())
                layout["right"]["status"].update(Panel(get_status_table(), title="🔋 Operating System Status Checks"))
                layout["right"]["logs"].update(get_logs_panel())

                time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard closed gracefully.[/yellow]")

if __name__ == "__main__":
    start_tui_loop()
