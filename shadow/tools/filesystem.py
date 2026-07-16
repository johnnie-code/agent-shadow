import os
import shutil
from typing import Dict, Any
from shadow.tools.base import Tool

class ReadFileTool(Tool):
    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a local file safely."

    @property
    def safety_level(self) -> int:
        return 0

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "The path to the file to read"}
            },
            "required": ["filepath"]
        }

    async def execute(self, filepath: str, **kwargs) -> Dict[str, Any]:
        try:
            if not os.path.exists(filepath):
                return {"success": False, "error": f"File '{filepath}' not found."}
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"success": True, "result": content}
        except Exception as e:
            return {"success": False, "error": str(e)}


class WriteFileTool(Tool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Create or overwrite a local file with the specified content."

    @property
    def safety_level(self) -> int:
        return 1

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "The path to the file"},
                "content": {"type": "string", "description": "The content to write to the file"}
            },
            "required": ["filepath", "content"]
        }

    async def execute(self, filepath: str, content: str, **kwargs) -> Dict[str, Any]:
        try:
            # Ensure folder exists
            dir_name = os.path.dirname(filepath)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return {"success": True, "result": f"File written successfully to {filepath}."}
        except Exception as e:
            return {"success": False, "error": str(e)}


class DeleteFileTool(Tool):
    @property
    def name(self) -> str:
        return "delete_file"

    @property
    def description(self) -> str:
        return "Delete a specified file. (Level 2: Sensitive action)."

    @property
    def safety_level(self) -> int:
        return 2

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "The path to the file to delete"}
            },
            "required": ["filepath"]
        }

    async def execute(self, filepath: str, **kwargs) -> Dict[str, Any]:
        try:
            if not os.path.exists(filepath):
                return {"success": False, "error": f"File '{filepath}' does not exist."}
            if os.path.isdir(filepath):
                shutil.rmtree(filepath)
            else:
                os.remove(filepath)
            return {"success": True, "result": f"Successfully deleted {filepath}."}
        except Exception as e:
            return {"success": False, "error": str(e)}
