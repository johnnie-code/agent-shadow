import asyncio
from typing import Dict, List, Callable, Any, Awaitable
from shadow.core.logging import log_decision

class EventTypes:
    PROVIDER_CONNECTED = "ProviderConnected"
    PROVIDER_FAILED = "ProviderFailed"
    MCP_CONNECTED = "MCPConnected"
    TOOL_EXECUTED = "ToolExecuted"
    SANDBOX_CREATED = "SandboxCreated"
    TASK_COMPLETED = "TaskCompleted"
    BACKGROUND_JOB_FINISHED = "BackgroundJobFinished"
    MEMORY_UPDATED = "MemoryUpdated"
    NOTIFICATIONS = "Notifications"


class EventBus:
    def __init__(self):
        # Maps event names to a list of async callback functions
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], Awaitable[None]]]] = {}

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """
        Subscribe an async callback function to an event type.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    async def publish(self, event_type: str, data: Dict[str, Any]):
        """
        Asynchronously dispatch/publish an event to all subscribed handlers.
        """
        log_decision(
            level="INFO",
            action=f"Publishing event: {event_type}",
            reasoning=f"Event dispatched with keys: {list(data.keys())}",
            result=f"Subscribers listening: {len(self._subscribers.get(event_type, []))}"
        )

        if event_type not in self._subscribers:
            return

        # Fire callbacks concurrently or sequentially depending on safety
        tasks = []
        for callback in self._subscribers[event_type]:
            # Guard against subscriber failure to keep event bus resilient
            tasks.append(self._safe_execute(callback, event_type, data))

        if tasks:
            await asyncio.gather(*tasks)

    async def _safe_execute(self, callback: Callable[[Dict[str, Any]], Awaitable[None]], event_type: str, data: Dict[str, Any]):
        try:
            await callback(data)
        except Exception as e:
            log_decision(
                level="ERROR",
                action=f"Error executing callback for event {event_type}",
                reasoning="A subscriber threw an unhandled exception.",
                error=str(e)
            )

# Global Event Bus Singleton
event_bus = EventBus()
