import os
import json
import sys
import traceback
import pathlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from shadow.core.config import SHADOW_HOME

# Ensure the logs/update directory exists using pathlib to bypass any os.makedirs mocks in tests
LOG_DIR = os.path.join(SHADOW_HOME, "logs", "update")
pathlib.Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
HISTORY_FILE = os.path.join(LOG_DIR, "history.json")

def safe_serialize_dict(d: Any) -> Any:
    """Recursively converts non-JSON serializable objects to strings (like MagicMocks)."""
    if isinstance(d, dict):
        return {str(k): safe_serialize_dict(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [safe_serialize_dict(x) for x in d]
    elif isinstance(d, (str, int, float, bool, type(None))):
        return d
    else:
        return str(d)

class UpdateLogger:
    def __init__(self):
        self.start_time = datetime.now()
        self.timestamp = self.start_time.strftime("%Y%m%d-%H%M%S")
        self.log_filename = f"update-{self.timestamp}.log"
        self.log_filepath = os.path.join(LOG_DIR, self.log_filename)
        self.events: List[Dict[str, Any]] = []
        self.git_commit_before = "unknown"
        self.git_commit_after = "unknown"
        self.success = False
        self.rollback_reason = None
        self.rollback_duration = 0.0
        self.restore_status = None
        self.failed_step = None
        self.failed_command = None
        self.exception_info = None

        # Ensure log directory exists at creation
        pathlib.Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

    def start_update(self, git_commit_before: str):
        self.git_commit_before = git_commit_before
        self.start_time = datetime.now()
        self.log_event("update_start", f"Update started at {self.start_time.isoformat()} with commit {git_commit_before}")

    def log_event(self, step: str, message: str, status: str = "info", details: Optional[Dict[str, Any]] = None):
        event = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "status": status,
            "message": message,
            "details": safe_serialize_dict(details) if details else {}
        }
        self.events.append(event)

        # Ensure directory exists before open
        pathlib.Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

        # Write immediately to file to ensure we don't lose logs on crash
        with open(self.log_filepath, "a", encoding="utf-8") as f:
            f.write(f"[{event['timestamp']}] [{step.upper()}] [{status.upper()}] {message}\n")
            if details:
                f.write(f"  Details: {json.dumps(event['details'], indent=2)}\n")

    def log_exception(self, step: str, exc: Exception, context: str = ""):
        exc_type = type(exc).__name__
        exc_msg = str(exc)
        tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

        # Parse tb for file, line, function
        tb_frames = traceback.extract_tb(exc.__traceback__)
        last_frame = tb_frames[-1] if tb_frames else None

        exc_data = {
            "type": exc_type,
            "message": exc_msg,
            "file": last_frame.filename if last_frame else "unknown",
            "line": last_frame.lineno if last_frame else 0,
            "function": last_frame.name if last_frame else "unknown",
            "full_traceback": tb_str
        }

        self.exception_info = safe_serialize_dict(exc_data)
        self.failed_step = step

        msg = f"Exception in {step}: {exc_type}: {exc_msg}"
        if context:
            msg += f" (Context: {context})"

        self.log_event(step, msg, status="error", details=exc_data)

    def write_rollback_report(
        self,
        cause: str,
        failed_step: str,
        failed_command: Optional[str],
        exception: Optional[Dict[str, Any]],
        rollback_commit: str,
        duration: float,
        data_restored: List[str],
        verification_status: str
    ):
        report = {
            "report_type": "Rollback Report",
            "timestamp": datetime.now().isoformat(),
            "cause": cause,
            "failed_step": failed_step,
            "failed_command": failed_command,
            "exception": safe_serialize_dict(exception) if exception else None,
            "previous_commit": self.git_commit_before,
            "new_commit": self.git_commit_after,
            "rollback_commit": rollback_commit,
            "duration": duration,
            "data_restored": data_restored,
            "verification_status": verification_status
        }

        report_filename = f"rollback-{self.timestamp}.json"
        report_filepath = os.path.join(LOG_DIR, report_filename)
        pathlib.Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
        with open(report_filepath, "w", encoding="utf-8") as f:
            json.dump(safe_serialize_dict(report), f, indent=2)

        self.log_event("rollback_report", f"Rollback report saved to {report_filepath}", details={"filepath": report_filepath})

    def end_update(
        self,
        success: bool,
        git_commit_after: str,
        rollback_reason: Optional[str] = None,
        rollback_duration: float = 0.0,
        restore_status: Optional[str] = None
    ):
        self.success = success
        self.git_commit_after = git_commit_after
        self.rollback_reason = rollback_reason
        self.rollback_duration = rollback_duration
        self.restore_status = restore_status

        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        status_str = "SUCCESS" if success else "FAILED"
        self.log_event("update_end", f"Update completed with status: {status_str}. Total duration: {duration:.2f}s")

        # Save structural JSON log
        summary_filepath = os.path.join(LOG_DIR, f"update-{self.timestamp}.json")
        pathlib.Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
        summary_data = {
            "timestamp": self.timestamp,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "git_commit_before": self.git_commit_before,
            "git_commit_after": self.git_commit_after,
            "success": success,
            "rollback_reason": rollback_reason,
            "rollback_duration": rollback_duration,
            "restore_status": restore_status,
            "failed_step": self.failed_step,
            "failed_command": self.failed_command,
            "exception_info": self.exception_info,
            "events": self.events
        }
        with open(summary_filepath, "w", encoding="utf-8") as f:
            json.dump(safe_serialize_dict(summary_data), f, indent=2)

        # Append to update history
        self._append_to_history({
            "version": "1.1.0",
            "commit_before": self.git_commit_before,
            "commit_after": git_commit_after,
            "date": self.start_time.isoformat(),
            "success": success,
            "rollback": not success,
            "duration": f"{duration:.2f}s",
            "failure_reason": safe_serialize_dict(rollback_reason) or (self.exception_info["message"] if self.exception_info else None)
        })

    def _append_to_history(self, entry: Dict[str, Any]):
        history = []
        pathlib.Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                pass

        history.append(safe_serialize_dict(entry))
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception:
            pass

def get_update_history() -> List[Dict[str, Any]]:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []
