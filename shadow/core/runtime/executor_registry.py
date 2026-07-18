import abc
from typing import Dict, Any

class BaseExecutor(abc.ABC):
    @abc.abstractmethod
    async def execute(self, task_title: str, task_description: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the task and return result."""
        pass

class ExecutorRegistry:
    def __init__(self):
        self._executors: Dict[str, BaseExecutor] = {}

    def register_executor(self, name: str, executor: BaseExecutor):
        self._executors[name.lower()] = executor

    def get_executor(self, name: str) -> BaseExecutor:
        return self._executors.get(name.lower())

    def list_executors(self) -> Dict[str, BaseExecutor]:
        return self._executors

# Global registry singleton
executor_registry = ExecutorRegistry()
