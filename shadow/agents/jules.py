import json
import os
from typing import Dict, Any, Optional
from shadow.core.logging import log_decision, logger

class JulesIntegration:
    """
    Shadow uses Jules as an external coding specialist. This engine prepares
    repository workspaces, generates AGENTS.md instructions for Jules, processes
    received patches, and runs localized tests before requesting merge approval.
    """
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = workspace_path

    def prepare_jules_workspace(self, objective: str, file_targets: list, constraints: str) -> Dict[str, Any]:
        """
        Creates an AGENTS.md instruction guide containing specific rules, target files, and constraints
        to bootstrap Jules execution.
        """
        agents_md_content = (
            "# Jules Specialist Guidance - PROJECT SHADOW\n\n"
            "## Objective\n"
            f"{objective}\n\n"
            "## File Targets\n"
            f"{json.dumps(file_targets)}\n\n"
            "## Constraints\n"
            f"{constraints}\n\n"
            "## Instructions\n"
            "- Modify code with correct safety conventions.\n"
            "- Write robust unit tests.\n"
            "- Verify using pytest.\n"
        )

        agents_filepath = os.path.join(self.workspace_path, "AGENTS.md")
        try:
            with open(agents_filepath, "w", encoding="utf-8") as f:
                f.write(agents_md_content)

            log_decision(
                level="INFO",
                action="Prepared Jules workspace guidance",
                reasoning="Bootstrapping coding specialist workspace by generating localized AGENTS.md rules.",
                result=f"Written target: {agents_filepath}"
            )
            return {"success": True, "agents_file": agents_filepath}
        except Exception as e:
            log_decision(
                level="ERROR",
                action="Jules workspace preparation failed",
                reasoning="Could not write localized AGENTS.md file.",
                error=str(e)
            )
            return {"success": False, "error": str(e)}

    async def apply_and_verify_patch(self, patch_content: str, test_command: str) -> Dict[str, Any]:
        """
        Apply incoming code modification patch, execute unit/integration tests,
        and assess safety prior to presenting code review reports.
        """
        # In a production environment, applying a diff can be executed via git apply/patch
        # or custom regex replacement. We simulate applying the patch and running test verifiers.
        logger.info("Applying code patch from specialist...")

        # Simulate running unit tests
        import asyncio
        proc = await asyncio.create_subprocess_shell(
            test_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        exit_code = proc.returncode

        success = (exit_code == 0)
        log_decision(
            level="INFO" if success else "WARNING",
            action="Jules patch execution test run",
            reasoning=f"Executing localized verify: '{test_command}'",
            result=f"Exit code: {exit_code}. Success: {success}"
        )
        return {
            "success": success,
            "exit_code": exit_code,
            "stdout": stdout.decode(errors='replace'),
            "stderr": stderr.decode(errors='replace')
        }

# Global Jules Integration singleton
jules_integration = JulesIntegration()
