from enum import Enum
from typing import Callable, Dict, List, Optional
from shadow.core.logging import logger

class RuntimeState(str, Enum):
    IDLE = "Idle"
    REASONING = "Reasoning"
    PLANNING = "Planning"
    EXECUTING = "Executing"
    WAITING = "Waiting"
    VALIDATING = "Validating"
    RETRYING = "Retrying"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    INTERRUPTED = "Interrupted"
    RESUMED = "Resumed"

class StateMachine:
    def __init__(self, initial_state: RuntimeState = RuntimeState.IDLE):
        self._state: RuntimeState = initial_state
        self._listeners: List[Callable[[RuntimeState, RuntimeState], None]] = []

    @property
    def current_state(self) -> RuntimeState:
        return self._state

    def add_listener(self, listener: Callable[[RuntimeState, RuntimeState], None]):
        self._listeners.append(listener)

    def transition_to(self, new_state: RuntimeState, reason: Optional[str] = None):
        if self._state == new_state:
            return

        old_state = self._state
        self._state = new_state

        reason_str = f" due to: {reason}" if reason else ""
        logger.info(f"StateMachine transitioned from {old_state.value} to {new_state.value}{reason_str}")

        for listener in self._listeners:
            try:
                listener(old_state, new_state)
            except Exception as e:
                logger.error(f"Error in StateMachine listener: {e}")

    def is_active(self) -> bool:
        return self._state in (
            RuntimeState.REASONING,
            RuntimeState.PLANNING,
            RuntimeState.EXECUTING,
            RuntimeState.WAITING,
            RuntimeState.VALIDATING,
            RuntimeState.RETRYING,
            RuntimeState.RESUMED
        )
