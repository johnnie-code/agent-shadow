from typing import Dict, Any, List, Callable, Type, Optional
from shadow.core.logging import logger

class SandboxPlugin:
    """Base class for all Sandbox Computer extension plugins."""
    @property
    def plugin_name(self) -> str:
        raise NotImplementedError

    def register(self, registry: 'SandboxPluginRegistry'):
        pass


class SandboxPluginRegistry:
    def __init__(self):
        self._runtimes: Dict[str, Callable[..., Any]] = {}
        self._browsers: Dict[str, Callable[..., Any]] = {}
        self._workers: Dict[str, Callable[..., Any]] = {}
        self._gpu_executors: Dict[str, Callable[..., Any]] = {}
        self._emulators: Dict[str, Callable[..., Any]] = {}

    def register_runtime(self, lang: str, handler: Callable[..., Any]):
        self._runtimes[lang] = handler
        logger.info(f"Sandbox Runtime Registered: '{lang}'")

    def register_browser(self, name: str, handler: Callable[..., Any]):
        self._browsers[name] = handler
        logger.info(f"Sandbox Browser Backend Registered: '{name}'")

    def register_worker(self, name: str, handler: Callable[..., Any]):
        self._workers[name] = handler
        logger.info(f"Sandbox Remote Worker Registered: '{name}'")

    def register_gpu_executor(self, name: str, handler: Callable[..., Any]):
        self._gpu_executors[name] = handler
        logger.info(f"Sandbox GPU Executor Registered: '{name}'")

    def register_emulator(self, name: str, handler: Callable[..., Any]):
        self._emulators[name] = handler
        logger.info(f"Sandbox Android Emulator Registered: '{name}'")

    def get_runtime(self, lang: str) -> Optional[Callable[..., Any]]:
        return self._runtimes.get(lang)

    def get_browser(self, name: str) -> Optional[Callable[..., Any]]:
        return self._browsers.get(name)

    def get_worker(self, name: str) -> Optional[Callable[..., Any]]:
        return self._workers.get(name)

    def get_gpu_executor(self, name: str) -> Optional[Callable[..., Any]]:
        return self._gpu_executors.get(name)

    def get_emulator(self, name: str) -> Optional[Callable[..., Any]]:
        return self._emulators.get(name)


# Global extensible plugin registry singleton
plugin_registry = SandboxPluginRegistry()
