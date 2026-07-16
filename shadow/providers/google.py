import httpx
from typing import List, Dict, Any
from shadow.providers.base import BaseProvider
from shadow.core.config import get_config

class GeminiProvider(BaseProvider):
    def __init__(self):
        config = get_config()
        self.api_key = config.gemini.api_key
        self.model = config.gemini.model
        self.api_base = config.gemini.api_base or "https://generativelanguage.googleapis.com/v1beta"

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        # gemini-2.5-flash: $0.075 / 1M input, $0.30 / 1M output tokens
        return (prompt_tokens * 0.075 / 1_000_000) + (completion_tokens * 0.30 / 1_000_000)

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Gemini API key is not configured.")

        # Convert Messages into Gemini format contents
        # system messages in Gemini can be passed via systemInstruction
        system_instruction = ""
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7)
            }
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        url = f"{self.api_base}/models/{kwargs.get('model', self.model)}:generateContent?key={self.api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=60.0)
            response.raise_for_status()
            data = response.json()

            content = data["candidates"][0]["content"]["parts"][0]["text"]

            # Gemini billing API tokens count
            usage_metadata = data.get("usageMetadata", {})
            prompt_tokens = usage_metadata.get("promptTokenCount", 0)
            completion_tokens = usage_metadata.get("candidatesTokenCount", 0)
            total_tokens = usage_metadata.get("totalTokenCount", 0)

            cost = self.calculate_cost(prompt_tokens, completion_tokens)

            return {
                "content": content,
                "tokens_used": total_tokens,
                "estimated_cost": cost,
                "model": kwargs.get('model', self.model)
            }
