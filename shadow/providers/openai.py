import httpx
from typing import List, Dict, Any
from shadow.providers.base import BaseProvider
from shadow.core.config import get_config
from shadow.core.logging import log_decision

class OpenAIProvider(BaseProvider):
    def __init__(self):
        config = get_config()
        self.api_key = config.openai.api_key
        self.model = config.openai.model
        self.api_base = config.openai.api_base or "https://api.openai.com/v1"

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        # standard gpt-4o-mini pricing: $0.150 / 1M input, $0.600 / 1M output tokens
        return (prompt_tokens * 0.150 / 1_000_000) + (completion_tokens * 0.600 / 1_000_000)

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("OpenAI API key is not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7)
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.api_base}/chat/completions", json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            prompt_tokens = data["usage"]["prompt_tokens"]
            completion_tokens = data["usage"]["completion_tokens"]
            total_tokens = data["usage"]["total_tokens"]

            cost = self.calculate_cost(prompt_tokens, completion_tokens)

            return {
                "content": content,
                "tokens_used": total_tokens,
                "estimated_cost": cost,
                "model": payload["model"]
            }
