import json
from datetime import datetime
from typing import Dict, Any
from shadow.core.database import get_db_connection
from shadow.providers.factory import get_provider
from shadow.core.logging import log_decision, logger

class ReflectionEngine:
    def __init__(self, provider_name: str = "mock"):
        self.provider = get_provider(provider_name)

    async def perform_daily_reflection(self) -> str:
        """
        Gathers completed and failed tasks, logs, and goals, and generates
        a strategic daily review with the AI reflection agent.
        """
        # Fetch metrics from SQLite DB
        conn = get_db_connection()
        cursor = conn.cursor()

        # Completed / failed tasks
        cursor.execute("SELECT title, category, status, error FROM tasks WHERE DATE(created_at) = DATE('now')")
        tasks_today = [dict(row) for row in cursor.fetchall()]

        # Recent logs
        cursor.execute("SELECT level, action, error FROM system_logs ORDER BY id DESC LIMIT 10")
        logs_today = [dict(row) for row in cursor.fetchall()]

        conn.close()

        prompt = (
            "You are the ReflectionAgent for PROJECT SHADOW. Your purpose is to run an evening audit of today's activities.\n"
            f"Tasks executed today:\n{json.dumps(tasks_today, indent=2)}\n\n"
            f"System logs today:\n{json.dumps(logs_today, indent=2)}\n\n"
            "Produce a structured daily reflection. Answer:\n"
            "1. What was completed successfully?\n"
            "2. What failed or encountered bugs?\n"
            "3. What was the overall alignment with our core mission?\n"
            "4. What strategy should change for tomorrow?\n\n"
            "Respond ONLY with a valid JSON containing 'reflection' key with your markdown formatting text, and a 'strategy_updates' list of strings."
        )

        try:
            res = await self.provider.chat([{"role": "system", "content": prompt}])
            data = json.loads(res["content"])
            reflection_text = data.get("reflection", "Completed today's reflection.")
            strategy_updates = data.get("strategy_updates", [])

            # Save reflection block to memory table so we don't overwrite user file data
            from shadow.memory.memory import memory_engine
            memory_engine.add_memory(
                category="insight",
                content=reflection_text,
                key=f"daily_reflection_{datetime.now().strftime('%Y-%m-%d')}",
                tags=["reflection", "daily_review"]
            )

            # Save strategy updates to memory
            for update in strategy_updates:
                memory_engine.add_memory(
                    category="preference",
                    content=update,
                    key="working_style_update",
                    tags=["strategy"]
                )

            log_decision(
                level="INFO",
                action="Daily evening reflection executed",
                reasoning="Strategic reflection compiles daily productivity gains and refines priorities.",
                result=f"Strategy updates recorded: {len(strategy_updates)}"
            )
            return reflection_text
        except Exception as e:
            log_decision(
                level="ERROR",
                action="Daily reflection failed",
                reasoning="Could not parse daily activities or generate reflection JSON.",
                error=str(e)
            )
            return f"Error during reflection: {e}"

# Global Reflection Engine singleton
reflection_engine = ReflectionEngine()
