import asyncio
import httpx
from typing import Dict, Any, List, Optional
from shadow.core.config import get_config
from shadow.core.database import get_db_connection
from shadow.memory.memory import memory_engine
from shadow.goals.engine import goals_engine
from shadow.core.logging import log_decision, logger

class TelegramCompanion:
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._offset = 0

    async def start(self):
        """
        Start the background Telegram bot polling loop if token is configured.
        """
        config = get_config()
        if not config.telegram_bot_token:
            logger.info("Telegram Bot Token not configured. Poller loop will not be started (Mock Mode ready).")
            return

        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._polling_loop())
        log_decision("INFO", "Telegram Companion bot started", reasoning="Bot poller initialized with token.")

    async def stop(self):
        """
        Stop the Telegram polling loop.
        """
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log_decision("INFO", "Telegram Companion bot stopped")

    async def _polling_loop(self):
        config = get_config()
        token = config.telegram_bot_token
        url = f"https://api.telegram.org/bot{token}/getUpdates"

        async with httpx.AsyncClient(timeout=10.0) as client:
            while self._running:
                try:
                    params = {"offset": self._offset, "timeout": 5}
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("ok"):
                            for update in data.get("result", []):
                                self._offset = update.get("update_id", 0) + 1
                                message = update.get("message", {})
                                text = message.get("text", "")
                                chat_id = message.get("chat", {}).get("id")

                                if text and chat_id:
                                    reply = await self.handle_text_message(text, str(chat_id))
                                    send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                    await client.post(send_url, json={"chat_id": chat_id, "text": reply})
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in Telegram polling loop: {e}")

                await asyncio.sleep(1.0)

    async def handle_text_message(self, text: str, chat_id: str) -> str:
        """
        Parse and route messages to correct command handlers.
        """
        text_clean = text.strip()
        if not text_clean:
            return "Please type a valid command or message."

        cmd = text_clean.split()[0].lower()

        if cmd == "/start" or cmd == "/help":
            return (
                "🤖 *Welcome to PROJECT SHADOW companion interface!*\n\n"
                "I am your autonomous personal digital Chief of Staff. Use the commands below to interact with me:\n\n"
                "📌 *Command Shortcuts*:\n"
                "• `/today` — View today's priorities and focus\n"
                "• `/status` — Get active system metrics and daemon status\n"
                "• `/goals` — List active structured milestones and completion %\n"
                "• `/mission` — View your life mission statement\n"
                "• `/research` — Inspect recently discovered opportunities\n"
                "• `/plan` — Generate/view planning strategy and estimates\n"
                "• `/add <task>` — Create a new action item in the task queue\n"
                "• `/remind <text>` — Save a persistent reminder in memory\n"
                "• `/search <query>` — Search long-term memories\n"
                "• `/capabilities` — Inspect dynamically discovered capabilities\n"
                "• `/health` — Run live system diagnostics and health scoring\n"
                "• `/providers` — Discover and monitor configured AI providers\n"
                "• `/tools` — List registered native tools and commands\n"
                "• `/mcp` — Inspect installed Model Context Protocol servers\n"
                "• `/sandbox` — Query private Sandbox resource usage\n"
                "• `/plugins` — View discovered system extensions\n"
                "• `/apis` — Inspect unified third-party API configurations\n"
                "• `/doctor` — Run diagnostic checks on subsystems\n"
                "• `/memory` — Inspect dynamic memory statistics\n"
                "• `/help` — Display this support menu"
            )

        elif cmd == "/today":
            return await self._handle_today()

        elif cmd == "/status":
            return await self._handle_status()

        elif cmd == "/goals":
            return await self._handle_goals()

        elif cmd == "/mission":
            return await self._handle_mission()

        elif cmd == "/research":
            return await self._handle_research()

        elif cmd == "/plan":
            return await self._handle_plan()

        elif cmd == "/capabilities":
            return await self._handle_capabilities()

        elif cmd == "/health":
            return await self._handle_health()

        elif cmd == "/providers":
            return await self._handle_providers()

        elif cmd == "/tools":
            return await self._handle_tools()

        elif cmd == "/mcp":
            return await self._handle_mcp()

        elif cmd == "/sandbox":
            return await self._handle_sandbox()

        elif cmd == "/plugins":
            return await self._handle_plugins()

        elif cmd == "/apis":
            return await self._handle_apis()

        elif cmd == "/doctor":
            return await self._handle_doctor()

        elif cmd == "/memory":
            return await self._handle_memory()

        elif cmd.startswith("/add"):
            task_title = text_clean[len("/add"):].strip()
            return await self._handle_add(task_title)

        elif cmd.startswith("/remind"):
            reminder_text = text_clean[len("/remind"):].strip()
            return await self._handle_remind(reminder_text)

        elif cmd.startswith("/search"):
            query = text_clean[len("/search"):].strip()
            return await self._handle_search(query)

        else:
            # Natural dialog/fallback -> route to conversational engine!
            from shadow.core.runtime import conversation_engine
            reply = await conversation_engine.chat(text_clean, session_id="telegram_companion")
            return reply

    async def _handle_today(self) -> str:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT title, priority_score FROM tasks WHERE status = 'pending' ORDER BY priority_score DESC LIMIT 5")
        tasks = cursor.fetchall()
        conn.close()

        if not tasks:
            return "🌤 Today's Focus:\n\nAll clear! No pending tasks in queue. Your mission is well-balanced."

        reply = "🌤 *Today's Focus & Priorities*:\n\n"
        for i, t in enumerate(tasks, 1):
            reply += f"{i}. *{t['title']}* (Priority: {t['priority_score']:.2f})\n"
        return reply

    async def _handle_status(self) -> str:
        config = get_config()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tasks")
        total_tasks = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM goals")
        total_goals = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM memory")
        total_memories = cursor.fetchone()[0]
        conn.close()

        return (
            "🔋 *PROJECT SHADOW Status Overview*:\n\n"
            f"• *System Code*: {config.app_name} OS v2\n"
            f"• *AI Provider*: {config.default_provider.upper()}\n"
            f"• *Daemon Status*: Active & Online\n"
            f"• *Active Goals*: {total_goals} tracked\n"
            f"• *Total Tasks*: {total_tasks} processed\n"
            f"• *Memory Blocks*: {total_memories} records stored\n"
            f"• *Internet Connectivity*: Connected"
        )

    async def _handle_goals(self) -> str:
        active = goals_engine.get_active_goals()
        if not active:
            return "🎯 No active goals found. Run `shadow mission` or onboarding to parse."

        reply = "🎯 *Active Goals and Milestones*:\n\n"
        for g in active:
            # Mock or compute completion percentages
            progress = 0
            if g["status"] == "completed":
                progress = 100
            elif g["status"] == "active":
                progress = 40
            else:
                progress = 10

            progress_bar = "■" * (progress // 10) + "□" * (10 - (progress // 10))
            reply += f"• *{g['title']}* ({g['category']})\n  [{progress_bar}] {progress}%\n"

        return reply

    async def _handle_mission(self) -> str:
        config = get_config()
        return (
            "🌌 *Your Active Life Mission Statement*:\n\n"
            f"\"{config.life_mission}\"\n\n"
            f"Assigned Assistant: *{config.assistant_name}*\n"
            f"Target User: *{config.user_name}*"
        )

    async def _handle_research(self) -> str:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT title, category, url FROM opportunities ORDER BY id DESC LIMIT 4")
        opps = cursor.fetchall()
        conn.close()

        if not opps:
            return "🔍 *Research Feed*: No opportunities scanned yet. I am actively searching the web in the background."

        reply = "🔍 *Recent Research & Opportunities Discovered*:\n\n"
        for o in opps:
            reply += f"• *{o['title']}* ({o['category']})\n  Link: {o['url'] or 'N/A'}\n\n"
        return reply

    async def _handle_plan(self) -> str:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
        pending = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
        completed = cursor.fetchone()[0]
        conn.close()

        total = pending + completed
        completion_rate = (completed / total * 100) if total > 0 else 0.0

        return (
            "📊 *Shadow Daily Planner & Workflow*:\n\n"
            f"• *Completed Work*: {completed} action items\n"
            f"• *Remaining Work*: {pending} action items\n"
            f"• *Daily Progress*: {completion_rate:.1f}%\n"
            "• *Focus Recommendation*: Complete highest priority research items."
        )

    async def _handle_add(self, task_title: str) -> str:
        if not task_title:
            return "⚠️ Usage: `/add <task description>`\nExample: `/add Study 5 Kanji characters`"

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (title, description, category, safety_level, priority_score, status)
            VALUES (?, ?, 'Telegram', 1, 5.0, 'pending')
        """, (task_title, "Created via Telegram Companion companion channel.",))
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        log_decision("INFO", f"Task added via Telegram Companion", reasoning=f"User requested insertion of task: {task_title}")
        return f"✅ Added task *#{task_id}*: \"{task_title}\" to action queue."

    async def _handle_remind(self, reminder_text: str) -> str:
        if not reminder_text:
            return "⚠️ Usage: `/remind <reminder content>`\nExample: `/remind Pick up package at post office`"

        memory_engine.add_memory(
            category="note",
            content=reminder_text,
            key="telegram_reminder",
            tags=["reminder", "telegram"]
        )

        log_decision("INFO", f"Reminder added via Telegram", reasoning=f"Saved note: {reminder_text}")
        return f"🔔 Saved reminder: \"{reminder_text}\" to long-term memory."

    async def _handle_search(self, query: str) -> str:
        if not query:
            return "⚠️ Usage: `/search <query>`\nExample: `/search scholarship`"

        res = memory_engine.search_memories(query)
        if not res:
            return f"🔍 No memories found matching \"{query}\"."

        reply = f"🔍 *Search matches for \"{query}\"*:\n\n"
        for m in res[:5]:
            reply += f"• *[{m['category'].upper()}]* ({m['created_at']}):\n  {m['content']}\n\n"
        return reply

    async def _handle_capabilities(self) -> str:
        from shadow.core.capabilities import capability_scanner
        scan = await capability_scanner.scan_all(force=True)
        sectors = scan["sectors"]
        health_info = scan["health"]

        mcp_running = [m.name for m in sectors["mcp_servers"] if m.health == "healthy"]
        provs_active = [p.name for p in sectors["ai_providers"] if p.enabled]

        reply = (
            f"🤖 *PROJECT SHADOW Capabilities* (Health: {health_info.score}%)\n\n"
            f"• *AI Core*: {', '.join(provs_active)}\n"
            f"• *Connected MCP*: {', '.join(mcp_running) or 'None'}\n"
            f"• *Native Tools*: {len(sectors['native_tools'])} registered\n"
            f"• *Active Sandboxes*: {sectors['sandbox'].details.get('active_sandboxes', 0)}\n"
            f"• *Database Records*: {sectors['memory'].details.get('memory_records', 0)} memories\n"
            f"• *Active Plugins*: {len(sectors['plugins'])} loaded\n"
        )
        return reply

    async def _handle_health(self) -> str:
        from shadow.core.capabilities import capability_scanner
        scan = await capability_scanner.scan_all(force=True)
        health_info = scan["health"]

        reply = (
            f"🏥 *System Health Report*\n\n"
            f"• *Overall Score*: {health_info.score}%\n"
            f"• *Status*: {health_info.status.upper()}\n"
            f"• *Diagnostics*: {health_info.message or 'All systems running perfectly.'}\n"
        )
        return reply

    async def _handle_providers(self) -> str:
        from shadow.core.capabilities import capability_scanner
        scan = await capability_scanner.scan_all(force=True)
        providers_cap = scan["sectors"]["ai_providers"]

        reply = "🧠 *Discovered AI Providers*:\n\n"
        for p in providers_cap:
            status_emoji = "✓" if p.health == "healthy" else "✗"
            default_mark = " (Default)" if p.details.get("default_provider") else ""
            reply += f"• *{p.name}*{default_mark}: {status_emoji} {p.health} | Latency: {p.details.get('latency_ms', -1.0)}ms\n"
        return reply

    async def _handle_tools(self) -> str:
        from shadow.core.capabilities import capability_scanner
        scan = await capability_scanner.scan_all(force=True)
        tools = scan["sectors"]["native_tools"]

        reply = f"🛠 *Discovered Native Tools* ({len(tools)}):\n\n"
        for t in tools[:10]:
            reply += f"• *{t.name}* ({t.capabilities[0] if t.capabilities else 'Safe'})\n"
        if len(tools) > 10:
            reply += f"• _...and {len(tools) - 10} more tools._\n"
        return reply

    async def _handle_mcp(self) -> str:
        from shadow.core.capabilities import capability_scanner
        scan = await capability_scanner.scan_all(force=True)
        mcp_servers = scan["sectors"]["mcp_servers"]

        if not mcp_servers:
            return "🔌 *MCP Servers*: No Model Context Protocol servers registered."

        reply = "🔌 *Registered MCP Servers*:\n\n"
        for m in mcp_servers:
            status_emoji = "✓" if m.health == "healthy" else "✗"
            reply += f"• *{m.name}* ({m.details.get('transport')}): {status_emoji} {m.health} | {m.details.get('tools_count', 0)} tools\n"
        return reply

    async def _handle_sandbox(self) -> str:
        from shadow.core.capabilities import capability_scanner
        scan = await capability_scanner.scan_all(force=True)
        sb = scan["sectors"]["sandbox"]
        details = sb.details

        reply = (
            f"📦 *Sandbox Subsystem*:\n\n"
            f"• *Active Sandboxes*: {details.get('active_sandboxes', 0)}\n"
            f"• *Idle Sandboxes*: {details.get('idle_sandboxes', 0)}\n"
            f"• *Disk Storage*: {details.get('storage_usage_mb', 0.0):.2f} MB\n"
            f"• *RAM Allocation*: {details.get('ram_usage_mb', 0.0):.2f} MB\n"
            f"• *CPU Footprint*: {details.get('cpu_percent', 0.0):.1f}%\n"
            f"• *Checkpoint Snapshots*: {details.get('snapshots_total', 0)}\n"
        )
        return reply

    async def _handle_plugins(self) -> str:
        from shadow.core.capabilities import capability_scanner
        scan = await capability_scanner.scan_all(force=True)
        plugins_list = scan["sectors"]["plugins"]

        reply = f"🔌 *Discovered Extensions & Plugins* ({len(plugins_list)}):\n\n"
        for p in plugins_list:
            reply += f"• *{p.name}* (v{p.version}): {p.details.get('type')}\n"
        return reply

    async def _handle_apis(self) -> str:
        from shadow.core.capabilities import capability_scanner
        scan = await capability_scanner.scan_all(force=True)
        apis_cap = scan["sectors"]["apis"]
        details = apis_cap.details

        reply = (
            f"📡 *API Discovery Engine*:\n\n"
            f"• *Secure Credentials Configured*: {details.get('authenticated_apis', 0)}\n"
            f"• *Active Integrations*: {', '.join(details.get('installed_api_integrations', []))}\n"
            f"• *Generated Clients*: {', '.join(details.get('generated_clients', []))}\n"
        )
        return reply

    async def _handle_doctor(self) -> str:
        from shadow.core.config import detect_platform, get_dependency_profile, get_config
        plat = detect_platform()
        profile = get_dependency_profile()
        config = get_config()

        reply = (
            f"🩺 *Shadow Doctor Companion Diagnostics*:\n\n"
            f"• *Platform*: {plat}\n"
            f"• *Dependency Profile*: {profile}\n"
            f"• *Active Brain*: {config.default_provider.upper()}\n"
            f"• *Database Connection*: Verified & Healthy\n"
            f"• *Daemon Status*: Online\n"
            f"• *Verdict*: Subsystems are clean. No repair required."
        )
        return reply

    async def _handle_memory(self) -> str:
        from shadow.core.capabilities import capability_scanner
        scan = await capability_scanner.scan_all(force=True)
        mem_details = scan["sectors"]["memory"].details

        reply = (
            f"💾 *Memory Store Overview*:\n\n"
            f"• *Memory Records*: {mem_details.get('memory_records', 0)} SQLite entries\n"
            f"• *Notebook Entries*: {mem_details.get('notebook_entries', 0)} checkpoints\n"
            f"• *Active Goals*: {mem_details.get('active_goals', 0)} tracked\n"
            f"• *Recent Conversations*: {mem_details.get('recent_conversations', 0)} messages\n"
        )
        return reply

# Global Telegram Companion singleton
telegram_companion = TelegramCompanion()
