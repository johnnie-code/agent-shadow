import uuid
from typing import Dict, Any, List, Optional

class ExecutionContext:
    def __init__(self, request: str, session_id: Optional[str] = None):
        self.context_id: str = str(uuid.uuid4())
        self.session_id: str = session_id or "default"
        self.original_request: str = request
        self.plan: List[Dict[str, Any]] = []
        self.current_task: Optional[Dict[str, Any]] = None
        self.completed_tasks: List[Dict[str, Any]] = []
        self.remaining_tasks: List[Dict[str, Any]] = []
        self.selected_tools: List[str] = []
        self.execution_history: List[Dict[str, Any]] = []
        self.generated_files: List[str] = []
        self.temporary_artifacts: List[str] = []
        self.validation_status: Dict[str, Any] = {}
        self.variables: Dict[str, Any] = {}
        self.metrics: Dict[str, Any] = {
            "start_time": None,
            "end_time": None,
            "retries": 0,
            "execution_time_seconds": 0.0,
            "tokens_used": 0,
            "cost": 0.0
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "session_id": self.session_id,
            "original_request": self.original_request,
            "plan": self.plan,
            "current_task": self.current_task,
            "completed_tasks": self.completed_tasks,
            "remaining_tasks": self.remaining_tasks,
            "selected_tools": self.selected_tools,
            "execution_history": self.execution_history,
            "generated_files": self.generated_files,
            "temporary_artifacts": self.temporary_artifacts,
            "validation_status": self.validation_status,
            "variables": self.variables,
            "metrics": self.metrics
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionContext":
        ctx = cls(data["original_request"], data.get("session_id"))
        ctx.context_id = data.get("context_id", ctx.context_id)
        ctx.plan = data.get("plan", [])
        ctx.current_task = data.get("current_task")
        ctx.completed_tasks = data.get("completed_tasks", [])
        ctx.remaining_tasks = data.get("remaining_tasks", [])
        ctx.selected_tools = data.get("selected_tools", [])
        ctx.execution_history = data.get("execution_history", [])
        ctx.generated_files = data.get("generated_files", [])
        ctx.temporary_artifacts = data.get("temporary_artifacts", [])
        ctx.validation_status = data.get("validation_status", {})
        ctx.variables = data.get("variables", {})
        ctx.metrics = data.get("metrics", ctx.metrics)
        return ctx
