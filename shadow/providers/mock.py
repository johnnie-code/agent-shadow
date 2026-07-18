import json
from typing import List, Dict, Any
from shadow.providers.base import BaseProvider

class MockProvider(BaseProvider):
    def __init__(self, fixed_response: str = "Mock response from Shadow AI Provider Layer."):
        self.fixed_response = fixed_response

    def initialize(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return 0.0

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        last_message = messages[-1]["content"] if messages else ""

        # If we need structured json outputs in mock responses, let's auto-generate them
        response_text = self.fixed_response
        if "JSON" in last_message.upper() or "schema" in last_message.lower():
            response_text = json.dumps({
                "status": "success",
                "message": "Mock structured JSON response",
                "opportunities": [
                    {
                        "title": "MEXT Scholarship 2026",
                        "description": "Prestigious fully-funded scholarship for studying in Japan.",
                        "url": "https://mext.go.jp",
                        "category": "Scholarship",
                        "source": "Web Search"
                    }
                ],
                "tasks": [
                    {
                        "title": "Read MEXT guidelines",
                        "description": "Understand eligibility and application timeline.",
                        "category": "Research",
                        "safety_level": 0,
                        "priority_score": 9.5
                    }
                ],
                "reasoning": "Mock scanner found matching high-impact opportunity aligned with your Japan learning goals.",
                "analysis": "This is a great match.",
                "reflection": "The day was productive and focused.",
                "action": "Proceeding with file updates.",
                "result": "Success"
            })

        return {
            "content": response_text,
            "tokens_used": 150,  # Retain standard mock token usage for backward test compatibility
            "estimated_cost": 0.0,
            "model": "shadow-mock-model"
        }

    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs):
        res = await self.chat(messages, **kwargs)
        yield res["content"]

    async def embed(self, texts: List[str], **kwargs) -> List[List[float]]:
        return [[0.0] * 1536 for _ in texts]

    def list_models(self) -> List[str]:
        return ["shadow-mock-model"]

    def supports_tools(self) -> bool:
        return True

    def supports_streaming(self) -> bool:
        return True

    def supports_images(self) -> bool:
        return True

    def supports_reasoning(self) -> bool:
        return True

    def supports_embeddings(self) -> bool:
        return True

    def supports_mcp(self) -> bool:
        return True

    def shutdown(self) -> None:
        pass
