import asyncio
import pytest
from unittest.mock import patch, MagicMock
from shadow.core.database import init_db, get_db_connection
from shadow.core.runtime import autonomous_runtime
from shadow.memory.memory import memory_engine

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

@pytest.mark.asyncio
async def test_conversation_engine_and_planning():
    init_db()

    # 1. Test Memory retrieve_context & ranking
    memory_engine.add_memory(
        category="preference",
        content="I prefer dark mode UI design.",
        key="theme_pref",
        tags=["ui", "theme"],
        importance_level="Important",
        importance_score=4.5
    )

    retrieved = memory_engine.retrieve_context("UI design", limit=1)
    assert len(retrieved) > 0
    assert "dark mode" in retrieved[0]["content"]

    # 2. Test ConversationEngine chat
    from shadow.core.runtime import conversation_engine
    reply = await conversation_engine.chat("Hello Ghost, advise on dark mode.")
    assert reply is not None

    # 3. Test TaskGenerator natural language task planning
    from shadow.goals.generator import TaskGenerator
    generator = TaskGenerator(provider_name="mock")
    tasks = await generator.generate_tasks_from_natural_language("Build GN notifications")
    assert len(tasks) > 0
    assert "title" in tasks[0]

@pytest.mark.asyncio
async def test_conversation_compression():
    init_db()

    # Clean prior session messages
    memory_engine.clear_conversation("test_compress_session")

    # Add 20 mock conversation lines to exceed threshold
    for i in range(20):
        memory_engine.add_conversation_message("test_compress_session", "user" if i % 2 == 0 else "assistant", f"Turn message {i}")

    # Compress conversation
    memory_engine.compress_conversation("test_compress_session", threshold=15)

    # Retrieve active history
    history = memory_engine.get_conversation_history("test_compress_session", limit=100)
    # The count should be kept light (around 7 messages: 1 system summary + 6 intact ones)
    assert len(history) < 15
    assert "[AUTONOMOUS COMPRESSION SUMMARY]" in history[0]["content"]
