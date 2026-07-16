from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the tool (must match schema and registry key)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A detailed description of what the tool does."""
        pass

    @property
    def safety_level(self) -> int:
        """
        0 = Read-only (Safe, automatic)
        1 = Local writes (Automatic)
        2 = Requires human approval (Git push, deletes, shell execution outside directory, etc.)
        """
        return 0

    @property
    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        """JSON schema representation of the tool parameters."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with the given keyword arguments.
        Returns a dictionary with 'success' and 'result' or 'error'.
        """
        pass
