import asyncio
import pytest
from shadow.core.events import event_bus
from shadow.core.scheduler import Scheduler

@pytest.mark.asyncio
async def test_event_bus():
    received_data = []

    async def sample_subscriber(data: dict):
        received_data.append(data)

    event_bus.subscribe("test_event", sample_subscriber)

    await event_bus.publish("test_event", {"message": "hello shadow"})

    assert len(received_data) == 1
    assert received_data[0]["message"] == "hello shadow"

@pytest.mark.asyncio
async def test_scheduler():
    scheduler_instance = Scheduler()
    execution_count = 0

    async def mock_job():
        nonlocal execution_count
        execution_count += 1

    scheduler_instance.add_interval_job("mock_job", 0.5, mock_job)
    await scheduler_instance.start()

    # Wait for execution
    await asyncio.sleep(0.8)
    await scheduler_instance.stop()

    assert execution_count >= 1
