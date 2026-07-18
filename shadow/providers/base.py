from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseProvider(ABC):
    def initialize(self) -> None:
        """Initialize the provider (load configs, connections, etc.)"""
        pass

    async def health_check(self) -> bool:
        """Perform a quick connectivity check. Returns True if healthy."""
        return True

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

    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs):
        """
        Streams a chat response back as an async generator of string chunks.
        """
        res = await self.chat(messages, **kwargs)
        yield res["content"]

    async def complete(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Simple text completion wrapper.
        """
        return await self.chat([{"role": "user", "content": prompt}], **kwargs)

    async def embed(self, texts: List[str], **kwargs) -> List[List[float]]:
        """
        Generate embeddings for a list of strings.
        """
        # Return mock embeddings as fallback
        return [[0.0] * 1536 for _ in texts]

    def list_models(self) -> List[str]:
        """List models supported/exposed by this provider."""
        return []

    def supports_tools(self) -> bool:
        """Whether the provider supports native tool execution / function calling."""
        return False

    def supports_streaming(self) -> bool:
        """Whether the provider supports streaming chat responses."""
        return False

    def supports_images(self) -> bool:
        """Whether the provider supports vision/image inputs."""
        return False

    def supports_reasoning(self) -> bool:
        """Whether the provider supports native deep reasoning/thinking."""
        return False

    def supports_embeddings(self) -> bool:
        """Whether the provider supports embedding generation."""
        return False

    def supports_mcp(self) -> bool:
        """Whether the provider is compatible with MCP tools."""
        return True

    @abstractmethod
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate cost of completion in USD.
        """
        pass

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a text string."""
        if not text:
            return 0
        return int(len(text.split()) * 1.3)

    def shutdown(self) -> None:
        """Clean up resources on shutdown."""
        pass
