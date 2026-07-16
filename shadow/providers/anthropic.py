import httpx
from typing import List, Dict, Any
from shadow.providers.base import BaseProvider
from shadow.core.config import get_config

class AnthropicProvider(BaseProvider):
    def __init__(self):
        config = get_config()
        self.api_key = config.anthropic.api_key
        self.model = config.anthropic.model
        self.api_base = config.anthropic.api_base or "https://api.anthropic.com/v1"

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        # standard claude-3-5-sonnet: $3.00 / 1M input, $15.00 / 1M output tokens
        return (prompt_tokens * 3.00 / 1_000_000) + (completion_tokens * 15.00 / 1_000_000)

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Anthropic API key is not configured.")

        # Convert openai formatted messages to anthropic system + user/assistant
        system_prompt = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": kwargs.get("model", self.model),
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.7)
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.api_base}/messages", json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()
            data = response.json()

            content = data["content"][0]["text"]
            prompt_tokens = data["usage"]["input_tokens"]
            completion_tokens = data["usage"]["output_tokens"]
            total_tokens = prompt_tokens + completion_tokens

            cost = self.calculate_cost(prompt_tokens, completion_tokens)

            return {
                "content": content,
                "tokens_used": total_tokens,
                "estimated_cost": cost,
                "model": payload["model"]
            }
