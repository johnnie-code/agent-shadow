import asyncio
import time
import traceback
from typing import Dict, Any, List, Optional
from shadow.core.database import get_db_connection
from shadow.core.logging import log_decision, logger
from shadow.core.config import get_config
from shadow.goals.priority import priority_engine
from shadow.goals.executor import execution_engine
from shadow.goals.generator import TaskGenerator
from shadow.goals.scanner import OpportunityScanner
from shadow.memory.memory import memory_engine

class AutonomousRuntime:
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.loop_interval = 30.0 # run loop every 30 seconds

    async def start(self):
        """
        Start the autonomous background reasoning loop.
        """
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self.reasoning_loop())
        log_decision("INFO", "Autonomous agent reasoning loop started", reasoning="Core daemon loop initialized.")

    async def stop(self):
        """
        Stop the reasoning loop.
        """
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log_decision("INFO", "Autonomous agent reasoning loop stopped")

    async def reasoning_loop(self):
        """
        Continuous Observe-Remember-Reason-Plan-Prioritize-Execute-Verify-Learn loop.
        """
        while self._running:
            try:
                # 1. OBSERVE
                obs = await self._observe()

                # 2. REMEMBER
                mem = await self._remember(obs)

                # 3. REASON
                actions = await self._reason(obs, mem)

                # 4. PLAN
                await self._plan(actions)

                # 5. PRIORITIZE
                await self._prioritize()

                # 6. EXECUTE
                executed = await self._execute()

                # 7. VERIFY
                await self._verify(executed)

                # 8. LEARN
                await self._learn(executed)

            except asyncio.CancelledError:
                break
            except Exception as e:
                log_decision(
                    level="ERROR",
                    action="Autonomous loop error",
                    reasoning="The continuous reasoning loop encountered an unhandled exception but will self-heal/recover.",
                    error=f"{str(e)}\n{traceback.format_exc()}"
                )

            await asyncio.sleep(self.loop_interval)

    async def _observe(self) -> Dict[str, Any]:
        """
        Observe: Check state of tasks, goals, opportunities, and logs.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE status = 'pending'")
        pending_tasks = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM opportunities WHERE status = 'new'")
        new_opps = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM goals WHERE status = 'pending'")
        pending_goals = cursor.fetchone()["count"]

        conn.close()

        # Try to observe battery status via tool registry if available
        battery_level = 100
        try:
            from shadow.tools.registry import tool_registry
            battery_tool = tool_registry.get_tool("android_battery")
            if battery_tool:
                res = await battery_tool.execute()
                if res.get("success"):
                    battery_level = res["result"].get("percentage", 100)
        except Exception:
            pass

        return {
            "pending_tasks": pending_tasks,
            "new_opportunities": new_opps,
            "pending_goals": pending_goals,
            "battery_level": battery_level,
            "timestamp": time.time()
        }

    async def _remember(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remember: Fetch relevant user preferences, mission, and instructions.
        """
        config = get_config()
        memories = memory_engine.search_memories("mission")
        return {
            "user_name": config.user_name,
            "life_mission": config.life_mission,
            "mission_memories_count": len(memories)
        }

    async def _reason(self, obs: Dict[str, Any], mem: Dict[str, Any]) -> List[str]:
        """
        Reason: Determine if we should scan for opportunities, trigger planner, or run tasks.
        """
        actions = []
        # If battery is low, restrict background scans and execution
        config = get_config()
        if obs["battery_level"] < config.battery_limit:
            log_decision(
                "WARNING",
                "Battery saver active",
                reasoning=f"Battery level {obs['battery_level']}% is below limit {config.battery_limit}%. Restricting execution."
            )
            return actions

        if obs["pending_tasks"] > 0:
            actions.append("execute_highest_task")

        if obs["new_opportunities"] > 0:
            actions.append("convert_opportunities")

        # Periodically scan for opportunities if queue is empty
        if obs["pending_tasks"] == 0 and obs["new_opportunities"] == 0:
            actions.append("scan_opportunities")

        return actions

    async def _plan(self, actions: List[str]):
        """
        Plan: Run scanner or task generator depending on reasoning.
        """
        config = get_config()

        if "scan_opportunities" in actions:
            queries = [q.strip() for q in "Japan scholarships, Remote AI jobs, GitHub autonomous agent".split(",")]
            try:
                scanner = OpportunityScanner()
                await scanner.scan(queries)
            except Exception as e:
                logger.error(f"Background opportunity scan failed: {e}")

        if "convert_opportunities" in actions:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM opportunities WHERE status = 'new' LIMIT 1")
            row = cursor.fetchone()
            conn.close()

            if row:
                try:
                    generator = TaskGenerator(provider_name=config.default_provider)
                    await generator.generate_tasks_for_opportunity(row["id"])
                except Exception as e:
                    logger.error(f"Background task generation failed: {e}")

    async def _prioritize(self):
        """
        Prioritize: Reprioritize and score tasks.
        """
        priority_engine.reprioritize_all_tasks()

    async def _execute(self) -> Optional[Dict[str, Any]]:
        """
        Execute: Find highest-priority pending task and run it.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, safety_level FROM tasks WHERE status = 'pending' ORDER BY priority_score DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        task_id = row["id"]
        title = row["title"]
        safety = row["safety_level"]

        if safety >= 2:
            # Requires explicit approval. Insert approval hold.
            await execution_engine.request_approval(task_id, title, {"description": "Auto-held by daemon runtime."})
            return {"task_id": task_id, "title": title, "status": "pending_approval", "success": False}

        # Run task
        res = await execution_engine.execute_task(task_id)
        return {
            "task_id": task_id,
            "title": title,
            "status": "completed" if res.get("success") else "failed",
            "success": res.get("success", False),
            "result": res.get("result"),
            "error": res.get("error")
        }

    async def _verify(self, executed: Optional[Dict[str, Any]]):
        """
        Verify: Validate task execution results.
        """
        if not executed:
            return

        task_id = executed["task_id"]
        status = executed["status"]

        if status == "completed":
            log_decision(
                "INFO",
                f"Autonomous verification passed",
                reasoning=f"Task #{task_id} successfully completed autonomously.",
                result=str(executed.get("result"))[:100]
            )
        elif status == "failed":
            log_decision(
                "ERROR",
                f"Autonomous verification warning/failure",
                reasoning=f"Task #{task_id} failed to execute autonomously.",
                error=executed.get("error")
            )

    async def _learn(self, executed: Optional[Dict[str, Any]]):
        """
        Learn: Log lessons learned/insights based on outcomes to memory.
        """
        if not executed or executed["status"] not in ["completed", "failed"]:
            return

        task_id = executed["task_id"]
        title = executed["title"]
        success = executed["success"]

        lesson = f"Task '{title}' (ID #{task_id}) was run autonomously. Result: {'Success' if success else 'Failure'}."
        memory_engine.add_memory(
            category="lesson_learned",
            content=lesson,
            key=f"task_lesson_{task_id}",
            tags=["learning", "execution_log"]
        )

# Global Autonomous Runtime singleton
autonomous_runtime = AutonomousRuntime()
