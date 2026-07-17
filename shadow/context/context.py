import os
import asyncio
from typing import Dict, Any, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from shadow.core.events import event_bus
from shadow.core.logging import logger
from shadow.core.config import SHADOW_HOME

class ContextFileHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if event.is_directory:
            return
        # We listen for specific text files we care about
        filename = os.path.basename(event.src_path)
        if filename in ["mission.md", "projects.md", "journal.md", "todo.md", "ideas.md", "notes.md", "knowledge.md"]:
            self.callback(filename, event.src_path)


class ContextEngine:
    def __init__(self, watch_dir: Optional[str] = None):
        self.watch_dir = watch_dir or SHADOW_HOME
        self.observer: Optional[Observer] = None
        self._cache: Dict[str, str] = {}
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """
        Register the main running asyncio loop to allow threadsafe event dispatch from watchdog.
        """
        self.loop = loop

    def read_context_file(self, filename: str) -> str:
        """
        Reads a file's content safely, returning an empty string if it doesn't exist.
        """
        filepath = os.path.join(self.watch_dir, filename)
        if not os.path.exists(filepath):
            return ""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                self._cache[filename] = content
                return content
        except Exception as e:
            logger.error(f"Error reading context file {filename}: {e}")
            return self._cache.get(filename, "")

    def get_unified_context(self) -> Dict[str, str]:
        """
        Load current state of all key files for prompt engineering and action validation.
        """
        files = [
            "mission.md", "projects.md", "journal.md", "todo.md",
            "ideas.md", "notes.md", "knowledge.md"
        ]
        return {f: self.read_context_file(f) for f in files}

    def start_monitoring(self):
        """
        Start directory watchdog to trigger async event_bus notifications when users modify files.
        """
        try:
            def handle_change(filename: str, path: str):
                logger.info(f"Context file changed: {filename}")
                # Threadsafe publish to event bus
                target_loop = self.loop
                if not target_loop:
                    try:
                        target_loop = asyncio.get_running_loop()
                    except RuntimeError:
                        pass

                if target_loop and target_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        event_bus.publish("context_file_updated", {
                            "filename": filename,
                            "filepath": path
                        }),
                        target_loop
                    )
                else:
                    logger.debug("No active event loop registered; skipped async event publishing.")

            event_handler = ContextFileHandler(handle_change)
            self.observer = Observer()
            self.observer.schedule(event_handler, path=self.watch_dir, recursive=False)
            self.observer.start()
            logger.info(f"ContextEngine started monitoring directory: '{self.watch_dir}'")
        except Exception as e:
            logger.error(f"Could not start file monitor: {e}")

    def stop_monitoring(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("ContextEngine file monitoring stopped.")

# Global Context Engine singleton
context_engine = ContextEngine()
