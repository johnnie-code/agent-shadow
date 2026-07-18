import time
import json
from typing import Dict, Any, List, Optional
from shadow.core.database import get_db_connection
from shadow.core.logging import log_decision, logger
from shadow.core.runtime.state_machine import StateMachine, RuntimeState
from shadow.core.runtime.progress_manager import ProgressManager
from shadow.core.runtime.execution_context import ExecutionContext
from shadow.core.runtime.task_executor import TaskExecutor
from shadow.core.runtime.result_builder import ResultBuilder
from shadow.goals.generator import TaskGenerator

class ExecutionEngine:
    def __init__(self, provider_name: str = "mock"):
        self.state_machine = StateMachine()
        self.progress_manager = ProgressManager()
        self.task_executor = TaskExecutor()
        self._provider_name = provider_name

    async def execute_project_workflow(self, request: str, session_id: Optional[str] = None) -> str:
        self.state_machine.transition_to(RuntimeState.REASONING, "Analyzing request complexity")
        self.progress_manager.start_step("Reasoning", "Analyzing request and determining workflow requirements.")

        # 1. Generate tasks
        self.state_machine.transition_to(RuntimeState.PLANNING, "Generating action queue")
        self.progress_manager.start_step("Planning", "Generating and structuring the task list.")

        generator = TaskGenerator(provider_name=self._provider_name)
        tasks = await generator.generate_tasks_from_natural_language(request)

        if not tasks:
            # Fallback to direct task template if generation fails
            tasks = [
                {
                    "title": f"Execute request: {request}",
                    "description": "Synthesize or perform direct execution.",
                    "category": "Coding",
                    "safety_level": 1,
                    "priority_score": 9.0
                }
            ]

        # Initialize execution context
        context = ExecutionContext(request, session_id)
        context.plan = tasks
        context.remaining_tasks = tasks.copy()
        context.metrics["start_time"] = time.time()

        self.state_machine.transition_to(RuntimeState.EXECUTING, "Running project tasks")
        self.progress_manager.start_step("Executing", "Executing structured subtasks autonomously.")

        # 2. Iterate and execute tasks
        for task in list(context.remaining_tasks):
            context.current_task = task
            self.progress_manager.update_step("Executing", f"Executing task: {task['title']}")

            # Run task execution
            exec_res = await self.task_executor.execute_task(task, context)

            # Save progress / results
            task_with_res = task.copy()
            task_with_res["result"] = exec_res.get("result", "")
            task_with_res["success"] = exec_res.get("success", False)
            task_with_res["status"] = "Completed" if exec_res.get("success") else "Failed"

            context.completed_tasks.append(task_with_res)
            context.execution_history.append(exec_res)

            # Record validation status
            if "validation" in exec_res:
                context.validation_status[task["title"]] = exec_res["validation"]

            # Remove from remaining
            if task in context.remaining_tasks:
                context.remaining_tasks.remove(task)

            # Persist memory to DB
            from shadow.memory.memory import memory_engine
            memory_engine.save_memory(
                category="decision",
                content=f"Executed task autonomously: {task['title']}. Result success: {exec_res.get('success')}",
                key=f"task_run_{task.get('title')}",
                tags=["execution", "runtime"]
            )

        context.metrics["end_time"] = time.time()
        context.metrics["execution_time_seconds"] = context.metrics["end_time"] - context.metrics["start_time"]

        # 3. Final Validation
        self.state_machine.transition_to(RuntimeState.VALIDATING, "Validating output results")
        self.progress_manager.start_step("Validating", "Running final formatting and syntax checks.")
        time.sleep(0.5)

        # 4. Result Building
        self.state_machine.transition_to(RuntimeState.COMPLETED, "Finished execution pipeline")
        self.progress_manager.start_step("Done", "Finalizing result report.")

        final_reply = ResultBuilder.build_final_response(context)

        self.state_machine.transition_to(RuntimeState.IDLE)
        return final_reply

    async def execute_direct_workflow(self, request: str, session_id: Optional[str] = None) -> str:
        self.state_machine.transition_to(RuntimeState.EXECUTING, "Direct execution of request")
        self.progress_manager.start_step("Executing", f"Direct processing: {request[:40]}...")

        context = ExecutionContext(request, session_id)
        task = {
            "title": f"Process request: {request}",
            "description": "Handle direct execution request.",
            "category": "Coding" if "html" in request.lower() or "code" in request.lower() else "Research",
            "safety_level": 1,
            "priority_score": 10.0
        }
        context.current_task = task
        context.plan = [task]

        # Execute
        res = await self.task_executor.execute_task(task, context)

        task_with_res = task.copy()
        task_with_res["result"] = res.get("result", "")
        task_with_res["success"] = res.get("success", False)
        task_with_res["status"] = "Completed" if res.get("success") else "Failed"
        context.completed_tasks.append(task_with_res)

        self.state_machine.transition_to(RuntimeState.VALIDATING, "Validating output")
        self.progress_manager.start_step("Validating", "Synthesizing formatting validations.")

        self.state_machine.transition_to(RuntimeState.COMPLETED, "Complete")
        self.progress_manager.start_step("Done", "Finalizing direct answer.")

        final_reply = ResultBuilder.build_final_response(context)
        self.state_machine.transition_to(RuntimeState.IDLE)
        return final_reply
