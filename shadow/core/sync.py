import os
import shutil
import difflib
from typing import Dict, Any, List, Optional
from shadow.core.sandbox import sandbox_manager

class FileSyncManager:
    @staticmethod
    def generate_diff(file_a: str, file_b: str) -> str:
        """Generates a standard unified diff between two files."""
        if not os.path.exists(file_a) and not os.path.exists(file_b):
            return ""

        content_a = []
        content_b = []

        if os.path.exists(file_a):
            with open(file_a, "r", encoding="utf-8", errors="replace") as f:
                content_a = f.readlines()
        if os.path.exists(file_b):
            with open(file_b, "r", encoding="utf-8", errors="replace") as f:
                content_b = f.readlines()

        diff = difflib.unified_diff(
            content_a, content_b,
            fromfile=file_a, tofile=file_b
        )
        return "".join(diff)

    @staticmethod
    def preview_changes(sandbox_id: str) -> List[Dict[str, Any]]:
        """Scans the sandbox workspace and lists all modified, created, or deleted files relative to the host project."""
        computer = sandbox_manager.get_sandbox(sandbox_id)
        if not computer:
            raise ValueError(f"Sandbox '{sandbox_id}' not found.")

        changes = []
        ws_dir = computer.workspace_dir

        for root, dirs, files in os.walk(ws_dir):
            # Skip hidden folders like .git or cache
            if ".git" in root or "node_modules" in root or ".venv" in root:
                continue

            for f in files:
                ws_path = os.path.join(root, f)
                rel_path = os.path.relpath(ws_path, ws_dir)

                # Check matching file in active host root (which is repository root or SHADOW_HOME context)
                host_path = os.path.abspath(rel_path)

                # Check status
                if not os.path.exists(host_path):
                    changes.append({
                        "file": rel_path,
                        "status": "created",
                        "diff": FileSyncManager.generate_diff("/dev/null", ws_path)
                    })
                else:
                    diff_text = FileSyncManager.generate_diff(host_path, ws_path)
                    if diff_text:
                        changes.append({
                            "file": rel_path,
                            "status": "modified",
                            "diff": diff_text
                        })

        return changes

    @staticmethod
    def detect_conflicts(sandbox_id: str) -> List[Dict[str, Any]]:
        """Detects if any files modified in the sandbox have been updated on the host since sandbox creation."""
        computer = sandbox_manager.get_sandbox(sandbox_id)
        if not computer:
            raise ValueError(f"Sandbox '{sandbox_id}' not found.")

        conflicts = []
        meta = computer.load_meta()
        created_at = float(meta.get("created_at", 0.0))

        ws_dir = computer.workspace_dir
        for root, dirs, files in os.walk(ws_dir):
            if ".git" in root or "node_modules" in root:
                continue
            for f in files:
                ws_path = os.path.join(root, f)
                rel_path = os.path.relpath(ws_path, ws_dir)
                host_path = os.path.abspath(rel_path)

                if os.path.exists(host_path):
                    # Check if host file mtime is greater than sandbox creation time AND is different
                    host_mtime = os.path.getmtime(host_path)
                    if host_mtime > created_at:
                        diff_text = FileSyncManager.generate_diff(host_path, ws_path)
                        if diff_text:
                            conflicts.append({
                                "file": rel_path,
                                "host_mtime": host_mtime,
                                "sandbox_created_at": created_at,
                                "message": "Host file has been modified after sandbox was initialized."
                            })
        return conflicts

    @classmethod
    def apply_sync(cls, sandbox_id: str, files_to_sync: Optional[List[str]] = None) -> Dict[str, Any]:
        """Performs real safe synchronization. Prevents silent overwriting."""
        computer = sandbox_manager.get_sandbox(sandbox_id)
        if not computer:
            raise ValueError(f"Sandbox '{sandbox_id}' not found.")

        # Check for conflicts
        conflicts = cls.detect_conflicts(sandbox_id)
        if conflicts:
            return {
                "success": False,
                "error": "Synchronization aborted due to conflicts.",
                "conflicts": conflicts
            }

        changes = cls.preview_changes(sandbox_id)
        synced_files = []

        # Create a rollback backup folder first
        backup_dir = os.path.join(computer.snapshots_dir, "sync_rollback_backup")
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
        os.makedirs(backup_dir, exist_ok=True)

        try:
            for change in changes:
                rel_path = change["file"]
                if files_to_sync and rel_path not in files_to_sync:
                    continue

                ws_file = os.path.join(computer.workspace_dir, rel_path)
                host_file = os.path.abspath(rel_path)

                # Backup host file if mtime or exists
                if os.path.exists(host_file):
                    backup_file = os.path.join(backup_dir, rel_path)
                    os.makedirs(os.path.dirname(backup_file), exist_ok=True)
                    shutil.copy2(host_file, backup_file)

                # Write/sync file to host
                os.makedirs(os.path.dirname(host_file), exist_ok=True)
                shutil.copy2(ws_file, host_file)
                synced_files.append(rel_path)

            return {
                "success": True,
                "synced_files": synced_files,
                "backup_dir": backup_dir
            }
        except Exception as e:
            # Automatic Rollback
            cls.rollback_sync(sandbox_id, backup_dir)
            return {
                "success": False,
                "error": f"Sync failed. Automatically rolled back. Details: {e}"
            }

    @classmethod
    def rollback_sync(cls, sandbox_id: str, backup_dir: str) -> bool:
        """Rolls back a sync operation using the generated backup directory."""
        if not os.path.exists(backup_dir):
            return False

        for root, dirs, files in os.walk(backup_dir):
            for f in files:
                backup_path = os.path.join(root, f)
                rel_path = os.path.relpath(backup_path, backup_dir)
                host_path = os.path.abspath(rel_path)

                os.makedirs(os.path.dirname(host_path), exist_ok=True)
                shutil.copy2(backup_path, host_path)
        return True
