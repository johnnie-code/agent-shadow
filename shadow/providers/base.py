from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseProvider(ABC):
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Send a chat message to the provider.
        Returns a dict:
        {
          "content": str,
          "tokens_used": int,
          "estimated_cost": float,
          "model": str
        }
        """
        pass

    @abstractmethod
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate cost of completion in USD.
        """
        pass
