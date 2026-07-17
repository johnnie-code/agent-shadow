import asyncio
import pytest
from unittest.mock import patch, MagicMock
from shadow.core.database import init_db, get_db_connection
from shadow.core.runtime import autonomous_runtime

@pytest.mark.asyncio
async def test_runtime_loop_lifecycle():
    init_db()

    # Start loop
    await autonomous_runtime.start()
    assert autonomous_runtime._running is True
    assert autonomous_runtime._task is not None

    # Stop loop
    await autonomous_runtime.stop()
    assert autonomous_runtime._running is False

@pytest.mark.asyncio
async def test_runtime_observe_and_reason():
    init_db()

    # Clean the database tables to ensure clean state
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks")
    cursor.execute("DELETE FROM opportunities")
    cursor.execute("DELETE FROM goals")
    conn.commit()
    conn.close()

    # Test observe method
    obs = await autonomous_runtime._observe()
    assert "pending_tasks" in obs
    assert "new_opportunities" in obs
    assert "pending_goals" in obs
    assert "battery_level" in obs

    # Test reasoning method
    actions = await autonomous_runtime._reason(obs, {})
    # Since battery is 100, and we have empty queues, it should offer to scan opportunities
    assert "scan_opportunities" in actions

    # Restrict battery to below limit (e.g. 10%)
    obs["battery_level"] = 10
    actions_low_battery = await autonomous_runtime._reason(obs, {})
    # Should restrict execution/scans due to low battery
    assert len(actions_low_battery) == 0
