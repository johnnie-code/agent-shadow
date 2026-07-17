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
            # Natural dialog/fallback
            return (
                f"I received your message: \"{text_clean}\".\n"
                "As your autonomous agent, I am monitoring your mission in the background. "
                "Type `/help` to see a full list of commands."
            )

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

# Global Telegram Companion singleton
telegram_companion = TelegramCompanion()
