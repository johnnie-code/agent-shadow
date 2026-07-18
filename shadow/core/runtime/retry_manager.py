from typing import Dict, Any, List, Optional, Callable, Awaitable
from shadow.core.logging import logger
from shadow.core.config import get_config

class RetryManager:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    async def execute_with_recovery(
        self,
        task_title: str,
        task_description: str,
        action_func: Callable[[], Awaitable[Dict[str, Any]]],
        fallback_func: Optional[Callable[[], Awaitable[Dict[str, Any]]]] = None
    ) -> Dict[str, Any]:
        retries = 0
        error_history = []

        while retries <= self.max_retries:
            try:
                if retries > 0:
                    logger.warning(f"Recovery try #{retries} for task: '{task_title}'")

                result = await action_func()
                if result.get("success", False):
                    return result

                error_msg = result.get("error", "Unknown error")
                error_history.append(error_msg)
                logger.error(f"Task '{task_title}' failed with error: {error_msg}")
            except Exception as e:
                error_msg = str(e)
                error_history.append(error_msg)
                logger.error(f"Execution exception for task '{task_title}': {error_msg}")

            retries += 1

        # If primary executor failed, try executing alternate/fallback path
        if fallback_func:
            logger.warning(f"Primary execution pathways failed for '{task_title}'. Attempting fallback strategy...")
            try:
                fallback_res = await fallback_func()
                if fallback_res.get("success", False):
                    return fallback_res
                error_history.append(fallback_res.get("error", "Fallback error"))
            except Exception as e:
                error_history.append(f"Fallback exception: {e}")

        return {
            "success": False,
            "error": f"Failed after {self.max_retries} retries and fallback attempts. Errors: {'; '.join(error_history)}"
        }
