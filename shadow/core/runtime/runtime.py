import asyncio
from typing import Dict, Any, List, Optional
from shadow.core.logging import logger
from shadow.core.runtime.intent_router import IntentRouter
from shadow.core.runtime.workflow_selector import WorkflowSelector, WorkflowType
from shadow.core.runtime.execution_engine import ExecutionEngine
from shadow.core.runtime.state_machine import RuntimeState

class ShadowRuntime:
    def __init__(self, provider_name: str = "mock"):
        self.intent_router = IntentRouter(provider_name=provider_name)
        self.workflow_selector = WorkflowSelector()
        self.execution_engine = ExecutionEngine(provider_name=provider_name)

    async def process_user_request(self, request: str, session_id: Optional[str] = None) -> str:
        logger.info(f"[Runtime] Processing user request: '{request}'")

        # 1. Intent Router
        classification = await self.intent_router.classify_intent(request)
        logger.info(f"[Runtime] Classified Intent: {classification['intent']} (Conf: {classification['confidence']:.2f})")

        # 2. Workflow Selector
        workflow = self.workflow_selector.select_workflow(request, classification)
        logger.info(f"[Runtime] Selected Workflow: {workflow.value}")

        # 3. Execution based on workflow selection
        if workflow == WorkflowType.DIRECT_CONVERSATION:
            # Route to normal conversation assistant
            from shadow.core.runtime import conversation_engine
            return await conversation_engine.chat(request, session_id=session_id)

        elif workflow == WorkflowType.DIRECT_EXECUTION:
            # Route to direct executor
            return await self.execution_engine.execute_direct_workflow(request, session_id=session_id)

        else:
            # Project workflow execution with full task queue pipeline
            return await self.execution_engine.execute_project_workflow(request, session_id=session_id)

    def get_metrics(self) -> Dict[str, Any]:
        """Expose runtime observability metrics."""
        return {
            "current_state": self.execution_engine.state_machine.current_state.value,
            "progress_steps": self.execution_engine.progress_manager.get_progress_steps(),
            "status": self.execution_engine.progress_manager.get_current_status(),
            "running_tasks": 1 if self.execution_engine.state_machine.is_active() else 0,
            "retries": 0,
            "execution_time_seconds": 0.0,
            "selected_providers": [self.execution_engine._provider_name]
        }

# Global Shadow Runtime singleton
shadow_runtime = ShadowRuntime()
