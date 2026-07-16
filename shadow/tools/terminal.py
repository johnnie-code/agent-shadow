import asyncio
from typing import Dict, Any
from shadow.tools.base import Tool

class TerminalTool(Tool):
    @property
    def name(self) -> str:
        return "terminal_execute"

    @property
    def description(self) -> str:
        return "Run a shell command safely inside Termux. (Level 2: requires human approval)."

    @property
    def safety_level(self) -> int:
        return 2

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to execute"}
            },
            "required": ["command"]
        }

    async def execute(self, command: str, **kwargs) -> Dict[str, Any]:
        try:
            # Run command asynchronously using subprocess
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await proc.communicate()

            return {
                "success": True,
                "exit_code": proc.returncode,
                "stdout": stdout.decode(errors='replace'),
                "stderr": stderr.decode(errors='replace')
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
