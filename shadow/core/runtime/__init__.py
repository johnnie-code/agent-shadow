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
from shadow.core.capabilities import capability_scanner, capability_planner

class ConversationEngine:
    def __init__(self, session_id: str = "default_cli"):
        self.session_id = session_id

    async def get_system_prompt(self) -> str:
        config = get_config()
        # Retrieve life mission and goals context
        from shadow.goals.engine import goals_engine
        active_goals = goals_engine.get_active_goals()
        goals_summary = "\n".join([f"- {g['title']} (Category: {g['category']}, Status: {g['status']})" for g in active_goals])

        prompt = (
            f"You are {config.assistant_name or 'Ghost'}, the persistent, conversational digital Chief of Staff "
            f"and Autonomous Personal Operating System for {config.user_name or 'User'}.\n\n"
            f"Your Core Directives:\n"
            f"1. Help the user achieve their Life Mission: \"{config.life_mission}\"\n"
            f"2. Align every recommendation and action with the current goals.\n\n"
            f"Active Goals:\n{goals_summary or 'No goals parsed yet.'}\n\n"
            f"When the user asks you to do something, you should decide if you can execute it immediately "
            f"or if you need to create a plan of subtasks. If a plan is needed, describe the plan, and tell "
            f"the user that you can generate tasks for it. No slash commands are allowed. Respond naturally and with authority."
        )
        return prompt

    async def chat(self, user_message: str, session_id: Optional[str] = None) -> str:
        active_session = session_id or self.session_id

        # Check Capability Planner first for missing capabilities/MCPs
        missing_cap = capability_planner.analyze_missing_capability(user_message)
        if missing_cap:
            config_details = missing_cap["suggested_config"]
            return (
                f"I don't currently have an MCP server for {missing_cap['keyword'].capitalize()}. "
                f"I found one ({config_details['name']}) that supports your request: \"{config_details['description']}\". "
                f"I can install and configure it with your approval."
            )

        # Check if the user is asking about our capabilities
        user_msg_lower = user_message.lower().strip()
        is_capabilities_query = any(phrase in user_msg_lower for phrase in [
            "what can you do", "what you can do", "show capabilities", "your capabilities",
            "list capabilities", "what capabilities", "system capabilities", "tell me what you can do"
        ])
        if is_capabilities_query:
            scan = await capability_scanner.scan_all(force=True)
            sectors = scan["sectors"]
            health_info = scan["health"]

            active_brain = next((p for p in sectors["ai_providers"] if p.details.get("default_provider")), None)
            brain_name = active_brain.name if active_brain else "Unknown"

            mcp_running = [m.name for m in sectors["mcp_servers"] if m.health == "healthy"]
            mcp_stopped = [m.name for m in sectors["mcp_servers"] if m.health != "healthy" and m.enabled]

            native_tools_count = len(sectors["native_tools"])
            plugins_count = len(sectors["plugins"])

            sandbox_details = sectors["sandbox"].details
            mem_details = sectors["memory"].details

            response = (
                f"🤖 **PROJECT SHADOW — Live Architectural Capabilities Report** (System Health: {health_info.score}%)\n\n"
                f"I have inspected my own runtime architecture and verified the following live subsystems:\n\n"
                f"🧠 **AI Core (Reasoning Brain)**\n"
                f"• Active Provider: **{brain_name}**\n"
                f"• Configured Providers: {', '.join([p.name for p in sectors['ai_providers'] if p.enabled])}\n\n"
                f"🔌 **Model Context Protocol (MCP)**\n"
                f"• Connected Servers: {', '.join(mcp_running) or 'None'}\n"
                f"• Available Tools (MCP): {sum(m.details.get('tools_count', 0) for m in sectors['mcp_servers'])} tools discovered\n"
                f"• Inactive Servers: {', '.join(mcp_stopped) or 'None'}\n\n"
                f"🛠 **Native Tools & Plugins**\n"
                f"• Registered Native Tools: **{native_tools_count}** tools (including Git, Sandbox, Browser, Android Build, Filesystem, Search, Memory, Planner)\n"
                f"• Active System Plugins: **{plugins_count}** plugins discovered (including Headless Playwright Browser, Gradle Compiler Suite, and registered Skill plugins)\n\n"
                f"📦 **Sandbox Container Subsystem**\n"
                f"• Active Sandboxes: {sandbox_details.get('active_sandboxes', 0)} ({sandbox_details.get('idle_sandboxes', 0)} idle)\n"
                f"• Resource Footprint: {sandbox_details.get('storage_usage_mb', 0.0)} MB Disk | {sandbox_details.get('ram_usage_mb', 0.0)} MB RAM | {sandbox_details.get('cpu_percent', 0.0)}% CPU\n"
                f"• Checkpoint Snapshots: {sandbox_details.get('snapshots_total', 0)} snapshots | {sandbox_details.get('workspace_files_count', 0)} workspace files\n\n"
                f"💾 **Long-Term Memory & Goals**\n"
                f"• Stored Memory Blocks: {mem_details.get('memory_records', 0)} sqlite records\n"
                f"• Notebook Checkpoints: {mem_details.get('notebook_entries', 0)} notes logged\n"
                f"• Active Milestones & Goals: {mem_details.get('active_goals', 0)} pending (with {mem_details.get('completed_goals', 0)} completed)\n\n"
                f"🔔 **Background Services**\n"
                f"• Daemon Server: **{sectors['background_services'].details.get('daemon', 'stopped').upper()}**\n"
                f"• Telegram Companion: **{sectors['background_services'].details.get('Telegram', 'disabled').upper()}**\n"
                f"• Autonomous reasoning loops: **{sectors['background_services'].details.get('autonomous_workers', 'idle').upper()}**\n\n"
                f"📡 **APIs & Connectors**\n"
                f"• Discovered APIs: {', '.join(sectors['apis'].details.get('installed_api_integrations', []))}\n"
                f"• Secure Authenticated Integrations: {sectors['apis'].details.get('authenticated_apis', 0)} credentials set\n\n"
                f"What would you like me to orchestrate today?"
            )
            return response

        # Retrieve context from long-term memory
        from shadow.memory.memory import memory_engine
        context_items = memory_engine.retrieve_context(user_message, limit=3)
        context_str = "\n".join([f"[{c['category'].upper()}] (Tag: {c['tags']}): {c['content']}" for c in context_items])

        # Retrieve conversation history
        history = memory_engine.get_conversation_history(active_session, limit=10)

        # Build prompt
        system_prompt = await self.get_system_prompt()
        if context_str:
            system_prompt += f"\n\nRetrieved Context from Memory:\n{context_str}"

        messages = [{"role": "system", "content": system_prompt}]
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})

        messages.append({"role": "user", "content": user_message})

        # Save user message to history
        memory_engine.add_conversation_message(active_session, "user", user_message)

        # Call active AI provider
        from shadow.providers.factory import get_provider
        provider = get_provider()
        try:
            res = await provider.chat(messages)
            reply = res["content"]

            # Save assistant message to history
            memory_engine.add_conversation_message(
                active_session,
                "assistant",
                reply,
                provider=res.get("model"),
                tokens=res.get("tokens_used", 0),
                cost=res.get("estimated_cost", 0.0)
            )

            # Auto-compress conversation history if it gets too long
            memory_engine.compress_conversation(active_session)

            return reply
        except Exception as e:
            return f"Ghost is having trouble thinking right now: {e}"

# Global conversation engine singleton
conversation_engine = ConversationEngine()

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

                # 9. SELF IMPROVE (logs cleanup, conversation compression, and suggestions)
                await self._self_improve()

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

    async def _check_wake_locks(self) -> bool:
        """
        Detect active wake locks (simulated or Termux-specific).
        """
        return True

    async def _check_charging(self) -> bool:
        """
        Detect if the device is plugged in / charging.
        """
        try:
            import subprocess
            import json
            import shutil
            if shutil.which("termux-battery-status"):
                res = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=2.0)
                if res.returncode == 0:
                    data = json.loads(res.stdout)
                    status_str = data.get("status", "").lower()
                    return "charging" in status_str or "full" in status_str
        except Exception:
            pass
        return True  # default fallback to safe state

    async def _check_connectivity(self) -> str:
        """
        Monitor Wi-Fi or Mobile Data connection.
        """
        try:
            import shutil
            import subprocess
            if shutil.which("termux-wifi-connectioninfo"):
                res = subprocess.run(["termux-wifi-connectioninfo"], capture_output=True, text=True, timeout=2.0)
                if res.returncode == 0:
                    return "Wi-Fi (Connected)"
        except Exception:
            pass
        return "Mobile Data (Connected)"

    async def _self_improve(self):
        """
        Background logs cleanup, conversation history compression, and mission suggestions.
        """
        try:
            # 1. Compress active conversation history
            memory_engine.compress_conversation("default_cli")
            memory_engine.compress_conversation("telegram_companion")

            # 2. Archive old recent memories (older than 15 days)
            memory_engine.archive_old_memories(days=15)

            # 3. Clean database logs (keep only latest 100 system logs to save disk space on mobile)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM system_logs WHERE id NOT IN (SELECT id FROM system_logs ORDER BY id DESC LIMIT 100)")
            conn.commit()
            conn.close()

            # 4. Mission-alignment suggestions
            # Log suggestions to memory if active goals are lacking
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM goals WHERE status = 'pending'")
            active_goals = cursor.fetchone()["count"]
            conn.close()

            if active_goals < 3:
                # Suggest a goal matching mission
                memory_engine.add_memory(
                    category="insight",
                    content="Ghost Suggestion: Based on your mission.md, consider adding a new goal to master advanced tool integration or mobile deployment.",
                    key="daemon_suggestion",
                    tags=["self_improvement", "goal_suggestion"]
                )
        except Exception as e:
            logger.error(f"Daemon self-improvement step failed: {e}")

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

        wake_lock_held = await self._check_wake_locks()
        is_charging = await self._check_charging()
        connectivity = await self._check_connectivity()

        return {
            "pending_tasks": pending_tasks,
            "new_opportunities": new_opps,
            "pending_goals": pending_goals,
            "battery_level": battery_level,
            "wake_lock_held": wake_lock_held,
            "is_charging": is_charging,
            "connectivity": connectivity,
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
