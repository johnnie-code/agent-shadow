import json
from typing import List, Dict, Any
from shadow.providers.base import BaseProvider

class MockProvider(BaseProvider):
    def __init__(self, fixed_response: str = "Mock response from Shadow AI Provider Layer."):
        self.fixed_response = fixed_response

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return 0.0

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        last_message = messages[-1]["content"] if messages else ""

        # If we need structured json outputs in mock responses, let's auto-generate them
        response_text = self.fixed_response
        if "JSON" in last_message.upper() or "schema" in last_message.lower():
            # Try to return a generic JSON if requested
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
            "tokens_used": 150,
            "estimated_cost": 0.0,
            "model": "shadow-mock-model"
        }
