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

    def initialize(self) -> None:
        pass

    async def health_check(self) -> bool:
        # Anthropic key validation check using a basic query with 1 max token limit
        if not self.api_key:
            return False
        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{self.api_base}/messages", json=payload, headers=headers, timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False

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

    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs):
        if not self.api_key:
            raise ValueError("Anthropic API key is not configured.")

        # Convert messages
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
            "temperature": kwargs.get("temperature", 0.7),
            "stream": True
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient() as client:
            async with client.stream("POST", f"{self.api_base}/messages", json=payload, headers=headers, timeout=60.0) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        import json
                        data_str = line[len("data: "):].strip()
                        try:
                            event_data = json.loads(data_str)
                            if event_data.get("type") == "content_block_delta":
                                delta = event_data["delta"].get("text", "")
                                if delta:
                                    yield delta
                        except Exception:
                            pass

    def list_models(self) -> List[str]:
        return ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-latest"]

    def supports_tools(self) -> bool:
        return True

    def supports_streaming(self) -> bool:
        return True

    def supports_images(self) -> bool:
        return True

    def supports_reasoning(self) -> bool:
        return True

    def supports_mcp(self) -> bool:
        return True

    def shutdown(self) -> None:
        pass
