import os
import shutil
import click
import typer
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from shadow.core.config import SHADOW_HOME, get_config
from shadow.core.database import init_db
from shadow.goals.engine import goals_engine
from shadow.memory.memory import memory_engine

console = Console()

def detect_android_capabilities() -> Dict[str, bool]:
    """
    Detect Termux/Android availability and tools.
    """
    is_termux = os.path.exists("/data/data/com.termux/files/usr") or "TERMUX_VERSION" in os.environ
    has_battery = shutil.which("termux-battery-status") is not None
    has_notification = shutil.which("termux-notification") is not None
    has_wifi = shutil.which("termux-wifi-connectioninfo") is not None
    has_bluetooth = shutil.which("termux-bluetooth-info") is not None
    has_location = shutil.which("termux-location") is not None
    has_camera = shutil.which("termux-camera-photo") is not None

    return {
        "is_termux": is_termux,
        "battery": has_battery,
        "notification": has_notification,
        "wifi": has_wifi,
        "bluetooth": has_bluetooth,
        "location": has_location,
        "camera": has_camera
    }

def initialize_storage():
    """
    Ensure core directory structures are initialized.
    """
    directories = [
        os.path.join(SHADOW_HOME, "backups"),
        os.path.join(SHADOW_HOME, "cache"),
        os.path.join(SHADOW_HOME, "logs"),
        os.path.join(SHADOW_HOME, "memory"),
        os.path.join(SHADOW_HOME, "plugins"),
        os.path.join(SHADOW_HOME, "config")
    ]
    for d in directories:
        os.makedirs(d, exist_ok=True)

def write_env_file(config_data: Dict[str, Any]):
    """
    Write gathered configs to the SHADOW_HOME/config/.env file.
    """
    config_dir = os.path.join(SHADOW_HOME, "config")
    os.makedirs(config_dir, exist_ok=True)
    env_path = os.path.join(config_dir, ".env")

    lines = [
        "# PROJECT SHADOW AUTONOMOUS CONFIGURATION\n",
        f"SHADOW_USER_NAME=\"{config_data.get('user_name', 'User')}\"\n",
        f"SHADOW_ASSISTANT_NAME=\"{config_data.get('assistant_name', 'Shadow')}\"\n",
        f"SHADOW_LIFE_MISSION=\"{config_data.get('life_mission', '')}\"\n",
        f"SHADOW_DEFAULT_PROVIDER=\"{config_data.get('provider', 'mock')}\"\n"
    ]

    provider = config_data.get('provider', 'mock')
    api_key = config_data.get('api_key', '')
    if provider != 'mock' and api_key:
        lines.append(f"SHADOW_{provider.upper()}__API_KEY=\"{api_key}\"\n")

    lines.append(f"SHADOW_NOTIFICATION_PREFERENCES=\"{config_data.get('notification_pref', 'terminal')}\"\n")

    if config_data.get("telegram_enabled", False):
        lines.append(f"SHADOW_TELEGRAM_BOT_TOKEN=\"{config_data.get('telegram_token', '')}\"\n")
        lines.append(f"SHADOW_TELEGRAM_CHAT_ID=\"{config_data.get('telegram_chat_id', '')}\"\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def write_mission_markdown(config_data: Dict[str, Any]):
    """
    Write generated mission.md file under SHADOW_HOME.
    """
    mission_path = os.path.join(SHADOW_HOME, "mission.md")

    goals_li = ""
    for goal in config_data.get("goals", []):
        goals_li += f"- {goal}\n"

    projects_li = ""
    for project in config_data.get("projects", []):
        projects_li += f"- {project}\n"

    content = f"""# MISSION

## Profile
- **User Name**: {config_data.get('user_name', 'User')}
- **Preferred Assistant Name**: {config_data.get('assistant_name', 'Shadow')}

## Life Mission
- {config_data.get('life_mission', 'Continuous autonomous improvement')}

# Long-Term Goals
{goals_li or '- Accomplish structured milestones'}

# Current Projects
{projects_li or '- Run and optimize PROJECT SHADOW'}
"""
    with open(mission_path, "w", encoding="utf-8") as f:
        f.write(content)

def run_onboarding(interactive: bool = True, defaults: Optional[Dict[str, Any]] = None):
    """
    Run first-launch interactive Rich-powered onboarding experience.
    """
    if not interactive:
        # Use defaults for automated testing
        data = defaults or {}
        user_name = data.get("user_name", "Test User")
        assistant_name = data.get("assistant_name", "Shadow")
        life_mission = data.get("life_mission", "Perform tests successfully")
        goals = data.get("goals", ["Pass unit tests"])
        projects = data.get("projects", ["Test Project Shadow"])
        provider = data.get("provider", "mock")
        api_key = data.get("api_key", "")
        telegram_enabled = data.get("telegram_enabled", False)
        telegram_token = data.get("telegram_token", "")
        telegram_chat_id = data.get("telegram_chat_id", "")
        notification_pref = data.get("notification_pref", "terminal")
    else:
        # Step 1: Welcome Screen
        console.print("\n")
        welcome_text = (
            "[bold white]Welcome to PROJECT SHADOW.[/bold white]\n\n"
            "This installer will configure your Autonomous Android-first AI Operating System.\n"
            "Shadow is designed to continuously align with your life mission, discover opportunities,\n"
            "and execute tasks autonomously directly on your device."
        )
        console.print(Panel(welcome_text, title="[bold red]PROJECT SHADOW — PHASE 2[/bold red]", border_style="red"))
        console.print("\n[dim]Initializing setup process...[/dim]\n")

        # Step 2: User Profile
        user_name = Prompt.ask("[bold green]What is your name?[/bold green]", default="User")
        assistant_name = Prompt.ask("[bold green]What is your preferred assistant name?[/bold green]", default="Shadow")

        # Step 3: Life Mission
        life_mission = Prompt.ask(
            "[bold green]Define your life mission statement[/bold green]\n"
            "[dim](e.g. Master Artificial Intelligence and build impactful global systems)[/dim]",
            default="Master software engineering and develop state-of-the-art AI agents"
        )

        # Step 4: Long-term goals
        goals_raw = Prompt.ask(
            "[bold green]Define long-term goals[/bold green] [dim](comma-separated list)[/dim]",
            default="Obtain a top-tier scholarship, Master Japanese Kanji, Deploy autonomous products"
        )
        goals = [g.strip() for g in goals_raw.split(",") if g.strip()]

        # Step 5: Current projects
        projects_raw = Prompt.ask(
            "[bold green]Define current projects[/bold green] [dim](comma-separated list)[/dim]",
            default="Integrate Android capability tools, Launch mobile companion daemon"
        )
        projects = [p.strip() for p in projects_raw.split(",") if p.strip()]

        # Step 6: Choose AI Provider
        console.print("\n[bold cyan]Choose your primary AI Provider:[/bold cyan]")
        console.print("  1. Gemini (Recommended for Termux/Android)")
        console.print("  2. OpenAI")
        console.print("  3. Claude")
        console.print("  4. Local Mock (Development & Offline Mode)")

        choice = Prompt.ask("[bold green]Select option (1-4)[/bold green]", choices=["1", "2", "3", "4"], default="4")
        providers_map = {"1": "gemini", "2": "openai", "3": "anthropic", "4": "mock"}
        provider = providers_map[choice]

        # Step 7: Secure API key configuration
        api_key = ""
        if provider != "mock":
            api_key = Prompt.ask(f"[bold green]Enter your {provider.upper()} API Key[/bold green]", password=True)

        # Step 8: Android Capability Detection
        console.print("\n[bold cyan]Detecting Android Capabilities...[/bold cyan]")
        caps = detect_android_capabilities()
        table = Table(title="Android Termux:API Capability Status")
        table.add_column("Capability / Tool", style="cyan")
        table.add_column("Status", style="bold")

        table.add_row("Termux Environment", "[green]✔ Detected[/green]" if caps["is_termux"] else "[yellow]✘ Desktop Simulator[/yellow]")
        table.add_row("Battery Status Monitoring", "[green]✔ Active[/green]" if caps["battery"] else "[dim]✘ Unavailable[/dim]")
        table.add_row("Notification Triggers", "[green]✔ Active[/green]" if caps["notification"] else "[dim]✘ Unavailable[/dim]")
        table.add_row("Wi-Fi Scan & Connection info", "[green]✔ Active[/green]" if caps["wifi"] else "[dim]✘ Unavailable[/dim]")
        table.add_row("Bluetooth Scanner Hooks", "[green]✔ Active[/green]" if caps["bluetooth"] else "[dim]✘ Unavailable[/dim]")
        table.add_row("GPS Location tracking", "[green]✔ Active[/green]" if caps["location"] else "[dim]✘ Unavailable[/dim]")
        table.add_row("Camera Capture", "[green]✔ Active[/green]" if caps["camera"] else "[dim]✘ Unavailable[/dim]")

        console.print(table)

        # Step 11: Telegram Setup
        telegram_enabled = Confirm.ask("\n[bold green]Do you want to configure the Telegram Companion Bot?[/bold green]", default=False)
        telegram_token = ""
        telegram_chat_id = ""
        if telegram_enabled:
            telegram_token = Prompt.ask("[bold green]Enter Telegram Bot Token[/bold green]")
            telegram_chat_id = Prompt.ask("[bold green]Enter your Telegram Chat ID / Authorized User ID[/bold green]")

        # Step 12: Notification Setup
        console.print("\n[bold cyan]Choose Notification Preference:[/bold cyan]")
        console.print("  1. Terminal logs only")
        console.print("  2. Native Android system notifications (Requires Termux:API)")
        console.print("  3. Suppress all notifications")
        pref_choice = Prompt.ask("[bold green]Select option (1-3)[/bold green]", choices=["1", "2", "3"], default="2" if caps["notification"] else "1")
        pref_map = {"1": "terminal", "2": "android", "3": "none"}
        notification_pref = pref_map[pref_choice]

    # Package configuration results
    config_payload = {
        "user_name": user_name,
        "assistant_name": assistant_name,
        "life_mission": life_mission,
        "goals": goals,
        "projects": projects,
        "provider": provider,
        "api_key": api_key,
        "telegram_enabled": telegram_enabled,
        "telegram_token": telegram_token,
        "telegram_chat_id": telegram_chat_id,
        "notification_pref": notification_pref
    }

    if interactive:
        console.print("\n[bold cyan][*] Initializing local operating storage...[/bold cyan]")
    # Step 9: Storage initialization
    initialize_storage()

    if interactive:
        console.print("[bold cyan][*] Setting up system database & schemas...[/bold cyan]")
    # Step 10: Database initialization
    init_db()

    if interactive:
        console.print("[bold cyan][*] Writing configurations and environment files...[/bold cyan]")
    # Step 14: Environment Validation & File Creation
    write_env_file(config_payload)
    write_mission_markdown(config_payload)

    # Force reset of the singleton config
    from shadow.core.config import reset_config
    reset_config(None)

    # Sync goals to database from generated mission.md
    try:
        mission_path = os.path.join(SHADOW_HOME, "mission.md")
        with open(mission_path, "r", encoding="utf-8") as f:
            md = f.read()
        goals_parsed = goals_engine.parse_mission_markdown(md)
        goals_engine.sync_goals_to_db(goals_parsed)
    except Exception as e:
        if interactive:
            console.print(f"[yellow]Warning: Could not sync mission goals to DB: {e}[/yellow]")

    # Record Onboarding Complete in DB
    memory_engine.add_memory(
        category="preference",
        content="true",
        key="onboarding_completed",
        tags=["system", "setup"]
    )

    if interactive:
        console.print("\n" + "="*50)
        console.print("[bold green]✔ Shadow successfully initialized.[/bold green]")
        console.print("[bold green]Mission accepted.[/bold green]")
        console.print("[bold green]Starting autonomous services...[/bold green]")
        console.print("="*50 + "\n")
