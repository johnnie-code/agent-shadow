import asyncio
import time
from datetime import datetime
from typing import Callable, Awaitable, List, Tuple, Optional
from shadow.core.events import event_bus
from shadow.core.logging import log_decision, logger

class Scheduler:
    def __init__(self):
        self._jobs: List[Tuple[str, float, Callable[[], Awaitable[None]], float]] = [] # (name, interval, func, last_run)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_hour: Optional[int] = None

    def add_interval_job(self, name: str, interval_seconds: float, func: Callable[[], Awaitable[None]]):
        """
        Add a periodic interval job.
        """
        self._jobs.append((name, interval_seconds, func, time.time()))
        logger.info(f"Scheduled interval job '{name}' every {interval_seconds}s.")

    async def start(self):
        """
        Start the background scheduler loop.
        """
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        log_decision("INFO", "Scheduler started", reasoning="Background scheduler runner initiated.")

        # Publish startup events
        await event_bus.publish("system_start", {"timestamp": time.time()})

    async def stop(self):
        """
        Stop the scheduler loop.
        """
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log_decision("INFO", "Scheduler stopped")

    async def _loop(self):
        # We also trigger standard times of day
        self._last_hour = datetime.now().hour

        while self._running:
            now = time.time()
            now_dt = datetime.now()

            # Check for hourly / morning / night triggers
            if now_dt.hour != self._last_hour:
                self._last_hour = now_dt.hour
                if now_dt.hour == 8:
                    await event_bus.publish("morning", {"hour": 8})
                elif now_dt.hour == 22:
                    await event_bus.publish("night", {"hour": 22})

            # Check and run scheduled jobs
            for i, (name, interval, func, last_run) in enumerate(self._jobs):
                if now - last_run >= interval:
                    # Update last run time before run to prevent dual triggering
                    self._jobs[i] = (name, interval, func, now)
                    asyncio.create_task(self._run_job(name, func))

            # Sleep 0.1s to be highly responsive and lightweight
            await asyncio.sleep(0.1)

    async def _run_job(self, name: str, func: Callable[[], Awaitable[None]]):
        start_time = time.time()
        try:
            log_decision("INFO", f"Executing scheduled job: {name}")
            await func()
            log_decision("INFO", f"Job {name} completed successfully.", duration=time.time() - start_time)
        except Exception as e:
            log_decision(
                "ERROR",
                f"Job {name} failed.",
                reasoning="Job threw an unhandled exception.",
                duration=time.time() - start_time,
                error=str(e)
            )

# Global Scheduler Singleton
scheduler = Scheduler()


# Configure predefined schedules and trigger event mappings
async def scheduled_research_job():
    await event_bus.publish("scheduled_research", {"topic": "AI news & Tech updates"})

async def scheduled_reflection_job():
    await event_bus.publish("scheduled_reflection", {"time": "evening_audit"})

async def scheduled_repo_analysis_job():
    await event_bus.publish("scheduled_repo_analysis", {"directory": "."})

async def scheduled_learning_job():
    await event_bus.publish("scheduled_learning", {"focus": "Japanese & Android"})


# Add standard system schedules
scheduler.add_interval_job("scheduled_research", 7200, scheduled_research_job) # 2 hours
scheduler.add_interval_job("scheduled_reflection", 14400, scheduled_reflection_job) # 4 hours
scheduler.add_interval_job("scheduled_repo_analysis", 28800, scheduled_repo_analysis_job) # 8 hours
scheduler.add_interval_job("scheduled_learning", 7200, scheduled_learning_job) # 2 hours
