import asyncio
from typing import Dict, Any
from shadow.tools.base import Tool

class GitTool(Tool):
    @property
    def name(self) -> str:
        return "git"

    @property
    def description(self) -> str:
        return "Perform standard Git operations like status, commit, and diff. Push is restricted."

    @property
    def safety_level(self) -> int:
        return 1

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subcommand": {"type": "string", "enum": ["status", "diff", "add", "commit", "push"], "description": "The git subcommand to run"},
                "args": {"type": "string", "description": "Optional parameters to pass to the git command"}
            },
            "required": ["subcommand"]
        }

    async def execute(self, subcommand: str, args: str = "", **kwargs) -> Dict[str, Any]:
        if subcommand == "push":
            # Pushing is a level 2 operation that is highly sensitive
            return {
                "success": False,
                "error": "Git push action is blocked. Push must be handled as an explicit Safety Level 2 action."
            }

        full_command = f"git {subcommand} {args}"
        try:
            proc = await asyncio.create_subprocess_shell(
                full_command,
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
