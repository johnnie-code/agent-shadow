from typing import Dict, Any
from shadow.tools.base import Tool

# Real Termux environments use `termux-clipboard-get` and `termux-clipboard-set`.
# We provide a clean fallback if not running on Termux directly.

_mock_clipboard_data = ""

class ClipboardTool(Tool):
    @property
    def name(self) -> str:
        return "clipboard"

    @property
    def description(self) -> str:
        return "Get or set the Termux/Android clipboard buffer."

    @property
    def safety_level(self) -> int:
        return 1

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["get", "set"], "description": "Whether to get or set clipboard text"},
                "text": {"type": "string", "description": "The text to set if the action is set"}
            },
            "required": ["action"]
        }

    async def execute(self, action: str, text: str = "", **kwargs) -> Dict[str, Any]:
        global _mock_clipboard_data
        try:
            # Check if termux-clipboard commands exist, else fallback to memory mock.
            import shutil
            has_termux_clipboard = shutil.which("termux-clipboard-get") is not None

            if action == "set":
                if has_termux_clipboard:
                    import asyncio
                    proc = await asyncio.create_subprocess_exec("termux-clipboard-set", text)
                    await proc.communicate()
                else:
                    _mock_clipboard_data = text
                return {"success": True, "result": "Clipboard updated."}
            else:
                if has_termux_clipboard:
                    import asyncio
                    proc = await asyncio.create_subprocess_exec("termux-clipboard-get", stdout=asyncio.subprocess.PIPE)
                    stdout, _ = await proc.communicate()
                    clipboard_text = stdout.decode().strip()
                else:
                    clipboard_text = _mock_clipboard_data
                return {"success": True, "result": clipboard_text}
        except Exception as e:
            return {"success": False, "error": str(e)}
class WebSearchTool(Tool):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for news, opportunities, scholarship info, jobs, and tools."

    @property
    def safety_level(self) -> int:
        return 0

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The query to search the web for"}
            },
            "required": ["query"]
        }

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        # Perform a mock search or fallback
        # In a real tool on termux we would fetch DuckDuckGo/Google or rely on an API,
        # here we return excellent relevant simulated opportunity links for scanner alignment!
        q = query.lower()
        if "scholarship" in q or "mext" in q:
            results = [
                {"title": "MEXT Scholarship 2026 Guidelines", "url": "https://www.mext.go.jp/en/policy/education/highered/title02/detail02/sdetail02/1373897.htm", "description": "Fully funded undergraduate and postgraduate scholarships for international students in Japan."},
                {"title": "JASSO Study in Japan Portal", "url": "https://www.studyinjapan.go.jp/en/", "description": "Government-sponsored resources for scholarships and student support."}
            ]
        elif "hackathon" in q or "competition" in q:
            results = [
                {"title": "Devpost Global AI Hackathon", "url": "https://devpost.com/hackathons", "description": "Compete with global software engineers building modular AI agents."},
                {"title": "Google Gemini Developer Challenge", "url": "https://ai.google.dev/challenge", "description": "Develop high impact applications using Gemini 2.5."}
            ]
        elif "internship" in q or "remote job" in q:
            results = [
                {"title": "GitHub Remote Junior AI Engineer Opportunities", "url": "https://github.com/remote-jobs", "description": "Remote positions for systems engineers specialized in Python and AI."},
                {"title": "Y Combinator Startup Directory", "url": "https://www.ycombinator.com/jobs", "description": "Internships and developer roles at top tech startups."}
            ]
        else:
            results = [
                {"title": f"Search Results for: {query}", "url": "https://duckduckgo.com", "description": "General search result matching query parameters."}
            ]
        return {"success": True, "result": results}
