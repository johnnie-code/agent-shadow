import typer
import asyncio
import json
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from shadow.core.mcp_manager import mcp_manager

mcp_app = typer.Typer(name="mcp", help="Manage external Model Context Protocol (MCP) servers.")
console = Console()

@mcp_app.callback(invoke_without_command=True)
def mcp_callback(ctx: typer.Context):
    """
    Model Context Protocol (MCP) Management interface.
    """
    from shadow.core.mcp_manager import mcp_available
    if not mcp_available:
        console.print("[bold red]Error: Model Context Protocol is unavailable (mcp package is not installed).[/bold red]")
        raise typer.Exit(code=1)
    if ctx.invoked_subcommand is None:
        mcp_list()

@mcp_app.command("install")
def mcp_install(
    name: str = typer.Argument(..., help="Unique name for the MCP server"),
    transport: str = typer.Option("stdio", "--transport", "-t", help="Transport protocol: 'stdio' or 'sse'"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="URL for SSE connections"),
    command: Optional[str] = typer.Option(None, "--cmd", "-c", help="Command to run stdio subprocess (e.g. 'uv', 'node', 'python')"),
    args: Optional[str] = typer.Option(None, "--args", "-a", help="Comma-separated arguments for stdio subprocess"),
    env: Optional[str] = typer.Option(None, "--env", "-e", help="JSON string representing environment variables"),
    auth: Optional[str] = typer.Option(None, "--auth", help="JSON string representing auth configuration (headers/keys)"),
    workspace: str = typer.Option("global", "--workspace", "-w", help="Workspace assignment scoping"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Human-readable server description"),
    version: Optional[str] = typer.Option(None, "--version", "-v", help="Server version")
):
    """
    Install and register an MCP server registry entry.
    """
    arg_list = [a.strip() for a in args.split(",")] if args else []
    env_dict = json.loads(env) if env else {}
    auth_dict = json.loads(auth) if auth else {}

    success = mcp_manager.install_server(
        name=name,
        transport=transport,
        url=url,
        command=command,
        args=arg_list,
        env=env_dict,
        authentication=auth_dict,
        workspace=workspace,
        description=description,
        version=version
    )

    if success:
        console.print(f"[green]✓ Successfully installed MCP server '{name}' to workspace '{workspace}'.[/green]")
    else:
        console.print(f"[red]Error installing MCP server '{name}'.[/red]")

@mcp_app.command("list")
def mcp_list(
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Filter by workspace scoping")
):
    """
    List all registered MCP servers, transport types, and connection status.
    """
    servers = mcp_manager.get_db_servers(workspace)
    if not servers:
        console.print("[yellow]No MCP servers registered.[/yellow]")
        return

    table = Table(title="Model Context Protocol (MCP) Servers")
    table.add_column("Name", style="bold green")
    table.add_column("Transport", style="cyan")
    table.add_column("Workspace", style="magenta")
    table.add_column("Status", style="bold yellow")
    table.add_column("Discovered Tools (Count)", style="white")

    for s in servers:
        try:
            tools = json.loads(s.get("tools") or "[]")
            tools_cnt = len(tools)
        except Exception:
            tools_cnt = 0

        status_style = "bold green" if s["status"] == "running" else "dim white" if s["status"] == "disabled" else "bold yellow"
        table.add_row(
            s["name"],
            s["transport"],
            s["workspace"] or "global",
            f"[{status_style}]{s['status']}[/{status_style}]",
            str(tools_cnt)
        )

    console.print(table)

@mcp_app.command("info")
def mcp_info(name: str = typer.Argument(..., help="Name of the MCP server")):
    """
    Show comprehensive configuration and discovered capabilities for a specific server.
    """
    server = mcp_manager.get_db_server(name)
    if not server:
        console.print(f"[red]MCP Server '{name}' not found.[/red]")
        return

    console.print(Panel.fit(
        f"[bold cyan]MCP Server Details: {server['name']}[/bold cyan]\n"
        f"Description:  {server.get('description') or 'None'}\n"
        f"Version:      {server.get('version') or 'N/A'}\n"
        f"Transport:    {server['transport']}\n"
        f"Status:       {server['status']}\n"
        f"Workspace:    {server['workspace'] or 'global'}\n"
        f"URL:          {server.get('url') or 'N/A'}\n"
        f"Command:      {server.get('command') or 'N/A'}\n"
        f"Args:         {server.get('args') or '[]'}\n"
        f"Authentication: {server.get('authentication') or '{}'}\n",
        title="[bold green]Registry Info[/bold green]"
    ))

@mcp_app.command("enable")
def mcp_enable(name: str = typer.Argument(..., help="Name of the MCP server")):
    """
    Enable a registered MCP server.
    """
    if mcp_manager.enable_server(name):
        console.print(f"[green]✓ MCP Server '{name}' enabled successfully.[/green]")
    else:
        console.print(f"[red]Error enabling MCP Server '{name}'.[/red]")

@mcp_app.command("disable")
def mcp_disable(name: str = typer.Argument(..., help="Name of the MCP server")):
    """
    Disable and disconnect a registered MCP server.
    """
    if mcp_manager.disable_server(name):
        console.print(f"[green]✓ MCP Server '{name}' disabled and stopped successfully.[/green]")
    else:
        console.print(f"[red]Error disabling MCP Server '{name}'.[/red]")

@mcp_app.command("remove")
def mcp_remove(name: str = typer.Argument(..., help="Name of the MCP server to uninstall")):
    """
    Completely remove an MCP server from the registry.
    """
    confirm = typer.confirm(f"Are you sure you want to completely uninstall MCP server '{name}'?")
    if confirm:
        if mcp_manager.remove_server(name):
            console.print(f"[green]✓ MCP Server '{name}' successfully removed.[/green]")
        else:
            console.print(f"[red]Error removing MCP Server '{name}'.[/red]")

@mcp_app.command("health")
def mcp_health(name: str = typer.Argument(..., help="Name of the MCP server")):
    """
    Trigger health checks and verify connectivity to the server.
    """
    console.print(f"Running connectivity and ping diagnostics on '{name}'...")
    healthy = asyncio.run(mcp_manager.health_check_server(name))
    if healthy:
        console.print(f"[green]✓ MCP Server '{name}' is ONLINE and responding perfectly.[/green]")
    else:
        console.print(f"[red]✗ MCP Server '{name}' is OFFLINE or returning errors.[/red]")

@mcp_app.command("logs")
def mcp_logs(name: str = typer.Argument(..., help="Name of the MCP server")):
    """
    Retrieve connection logs and execution traces for a server.
    """
    from shadow.core.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT level, action, reasoning, error, created_at FROM system_logs
        WHERE action LIKE ? OR reasoning LIKE ?
        ORDER BY id DESC LIMIT 15
    """, (f"%{name}%", f"%{name}%"))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        console.print(f"[yellow]No logged traces found matching server '{name}'.[/yellow]")
        return

    table = Table(title=f"Log Traces for MCP Server: '{name}'")
    table.add_column("Timestamp", style="dim")
    table.add_column("Level", style="bold yellow")
    table.add_column("Action Summary", style="green")
    table.add_column("Details/Error")

    for r in rows:
        table.add_row(r["created_at"], r["level"], r["action"], r["error"] or r["reasoning"] or "")

    console.print(table)

@mcp_app.command("tools")
def mcp_tools(name: Optional[str] = typer.Option(None, "--server", "-s", help="Server name")):
    """
    List automatically discovered tools.
    """
    servers = [mcp_manager.get_db_server(name)] if name else mcp_manager.get_db_servers()
    servers = [s for s in servers if s]

    table = Table(title="Discovered MCP Tools")
    table.add_column("Server", style="cyan")
    table.add_column("Tool Name", style="bold green")
    table.add_column("Permission Level", style="yellow")

    for s in servers:
        try:
            tools = json.loads(s.get("tools") or "[]")
            for t in tools:
                perm = mcp_manager.get_permission(s["name"], t)
                table.add_row(s["name"], t, perm)
        except Exception:
            pass

    console.print(table)

@mcp_app.command("resources")
def mcp_resources(name: Optional[str] = typer.Option(None, "--server", "-s", help="Server name")):
    """
    List automatically discovered resources.
    """
    servers = [mcp_manager.get_db_server(name)] if name else mcp_manager.get_db_servers()
    servers = [s for s in servers if s]

    table = Table(title="Discovered MCP Resources")
    table.add_column("Server", style="cyan")
    table.add_column("Resource URI", style="bold green")

    for s in servers:
        try:
            res = json.loads(s.get("resources") or "[]")
            for r in res:
                table.add_row(s["name"], r)
        except Exception:
            pass

    console.print(table)

@mcp_app.command("prompts")
def mcp_prompts(name: Optional[str] = typer.Option(None, "--server", "-s", help="Server name")):
    """
    List automatically discovered prompts.
    """
    servers = [mcp_manager.get_db_server(name)] if name else mcp_manager.get_db_servers()
    servers = [s for s in servers if s]

    table = Table(title="Discovered MCP Prompts")
    table.add_column("Server", style="cyan")
    table.add_column("Prompt Name", style="bold green")

    for s in servers:
        try:
            prompts = json.loads(s.get("prompts") or "[]")
            for p in prompts:
                table.add_row(s["name"], p)
        except Exception:
            pass

    console.print(table)
