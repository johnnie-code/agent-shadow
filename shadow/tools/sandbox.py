from typing import Dict, Any, Optional
from shadow.tools.base import Tool
from shadow.core.sandbox import sandbox_manager

class SandboxExecuteTool(Tool):
    @property
    def name(self) -> str:
        return "sandbox_execute"

    @property
    def description(self) -> str:
        return (
            "Create a sandbox, clone a repository or copy code, modify files, run tests, "
            "and safely compile code within Ghost's private sandbox computer before syncing results."
        )

    @property
    def safety_level(self) -> int:
        return 2 # Requires explicit human/policy approval on Level 2

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "destroy", "execute_command", "clone", "snapshot", "restore", "sync_to_host", "notebook_update"],
                    "description": "The sandbox management action to trigger"
                },
                "sandbox_id": {"type": "string", "description": "Unique identifier of the sandbox computer"},
                "sandbox_type": {"type": "string", "description": "Target profile, e.g., 'python', 'node', 'android'"},
                "command": {"type": "string", "description": "Command to execute inside the sandbox workspace (e.g. 'pytest' or 'npm test')"},
                "repo_url": {"type": "string", "description": "The remote Git URL to clone inside the sandbox"},
                "snapshot_name": {"type": "string", "description": "Name for snapshots or restore operations"},
                "src_rel_path": {"type": "string", "description": "Relative source path inside the workspace to copy"},
                "host_dest_path": {"type": "string", "description": "Target absolute path on host device"},
                "notebook_key": {"type": "string", "description": "Notebook dictionary section key to modify"},
                "notebook_value": {"type": "string", "description": "Goal or text message to log inside section"}
            },
            "required": ["action", "sandbox_id"]
        }

    async def execute(
        self,
        action: str,
        sandbox_id: str,
        sandbox_type: str = "generic",
        command: Optional[str] = None,
        repo_url: Optional[str] = None,
        snapshot_name: Optional[str] = None,
        src_rel_path: Optional[str] = None,
        host_dest_path: Optional[str] = None,
        notebook_key: Optional[str] = None,
        notebook_value: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        try:
            if action == "create":
                computer = sandbox_manager.create_sandbox(sandbox_id, sandbox_type)
                meta = computer.load_meta()
                return {"success": True, "result": f"Sandbox '{sandbox_id}' of type '{sandbox_type}' created successfully.", "metadata": meta}

            elif action == "destroy":
                success = sandbox_manager.destroy_sandbox(sandbox_id)
                return {"success": success, "result": f"Sandbox '{sandbox_id}' destroyed successfully." if success else "Failed to destroy sandbox."}

            computer = sandbox_manager.get_sandbox(sandbox_id)
            if not computer:
                return {"success": False, "error": f"Sandbox '{sandbox_id}' not found."}

            if action == "execute_command":
                if not command:
                    return {"success": False, "error": "Command parameter is required for execution."}
                res = await computer.execute_terminal(command)
                return {"success": True, "result": res}

            elif action == "clone":
                if not repo_url:
                    return {"success": False, "error": "repo_url parameter is required for cloning."}
                res = await computer.clone_repository(repo_url)
                return res

            elif action == "snapshot":
                if not snapshot_name:
                    return {"success": False, "error": "snapshot_name is required."}
                success = sandbox_manager.snapshot_sandbox(sandbox_id, snapshot_name)
                return {"success": success, "result": f"Snapshot '{snapshot_name}' saved." if success else "Failed."}

            elif action == "restore":
                if not snapshot_name:
                    return {"success": False, "error": "snapshot_name is required."}
                success = sandbox_manager.restore_snapshot(sandbox_id, snapshot_name)
                return {"success": success, "result": f"Snapshot '{snapshot_name}' restored." if success else "Failed."}

            elif action == "sync_to_host":
                if not src_rel_path or not host_dest_path:
                    return {"success": False, "error": "src_rel_path and host_dest_path are required."}
                success = computer.sync_results_to_host(src_rel_path, host_dest_path)
                return {"success": success, "result": f"Synced '{src_rel_path}' to host path '{host_dest_path}'." if success else "Sync failed."}

            elif action == "notebook_update":
                if not notebook_key or not notebook_value:
                    return {"success": False, "error": "notebook_key and notebook_value are required."}
                computer.update_notebook(notebook_key, notebook_value)
                return {"success": True, "result": f"Updated AI Notebook section '{notebook_key}'."}

            return {"success": False, "error": f"Unknown sandbox action: '{action}'."}

        except Exception as e:
            return {"success": False, "error": str(e)}
