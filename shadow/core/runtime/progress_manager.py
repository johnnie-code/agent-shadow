import time
from typing import Dict, Any, List, Optional
from shadow.core.logging import logger

class ProgressManager:
    def __init__(self):
        self._progress_steps: List[Dict[str, Any]] = []
        self._current_step_name: Optional[str] = None
        self._current_step_start: float = 0.0

    def start_step(self, step_name: str, message: str = ""):
        if self._current_step_name:
            self.complete_step(self._current_step_name, "Auto-completed on starting new step.")

        self._current_step_name = step_name
        self._current_step_start = time.time()

        step_info = {
            "name": step_name,
            "status": "Running",
            "message": message,
            "start_time": self._current_step_start,
            "end_time": None,
            "duration": 0.0
        }
        self._progress_steps.append(step_info)
        logger.info(f"[Progress] Started step: {step_name} - {message}")

    def update_step(self, step_name: str, message: str):
        for step in self._progress_steps:
            if step["name"] == step_name:
                step["message"] = message
                logger.info(f"[Progress Update] {step_name}: {message}")
                break

    def complete_step(self, step_name: str, message: str = ""):
        now = time.time()
        for step in self._progress_steps:
            if step["name"] == step_name and step["status"] == "Running":
                step["status"] = "Completed"
                step["message"] = message or step["message"]
                step["end_time"] = now
                step["duration"] = now - step["start_time"]
                logger.info(f"[Progress] Completed step: {step_name} - {step['message']} (Duration: {step['duration']:.2f}s)")
                break

        if self._current_step_name == step_name:
            self._current_step_name = None
            self._current_step_start = 0.0

    def fail_step(self, step_name: str, error_message: str):
        now = time.time()
        for step in self._progress_steps:
            if step["name"] == step_name and step["status"] == "Running":
                step["status"] = "Failed"
                step["message"] = error_message
                step["end_time"] = now
                step["duration"] = now - step["start_time"]
                logger.error(f"[Progress] Failed step: {step_name} - {error_message}")
                break

        if self._current_step_name == step_name:
            self._current_step_name = None
            self._current_step_start = 0.0

    def get_progress_steps(self) -> List[Dict[str, Any]]:
        return self._progress_steps

    def get_current_status(self) -> str:
        if self._current_step_name:
            elapsed = time.time() - self._current_step_start
            return f"{self._current_step_name}... ({elapsed:.1f}s)"
        return "Idle"
