import httpx
from typing import Dict, Any
from shadow.tools.base import Tool

class HTTPTool(Tool):
    @property
    def name(self) -> str:
        return "http_request"

    @property
    def description(self) -> str:
        return "Perform standard HTTP requests (GET, POST) to fetch external context or interact with APIs."

    @property
    def safety_level(self) -> int:
        return 0

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": ["GET", "POST"], "description": "The HTTP verb"},
                "url": {"type": "string", "description": "The URL to send request to"},
                "headers": {"type": "object", "description": "JSON dict of headers"},
                "payload": {"type": "object", "description": "JSON dict body for POST request"}
            },
            "required": ["method", "url"]
        }

    async def execute(self, method: str, url: str, headers: Dict[str, Any] = None, payload: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, timeout=15.0)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=payload, timeout=15.0)
                else:
                    return {"success": False, "error": f"HTTP method '{method}' not supported."}

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "body": response.text[:20000] # Cap output length for prompt safety
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
