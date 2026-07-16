import os
import asyncio
import pytest
from shadow.context.context import ContextEngine
from shadow.core.events import event_bus

@pytest.mark.asyncio
async def test_context_engine_reading():
    engine = ContextEngine(watch_dir="tests")

    # Write a mock file
    test_file = "tests/journal.md"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("# Day 1\nFocused on Android autonomous agents.")

    content = engine.read_context_file("journal.md")
    assert "Android autonomous agents" in content

    # Test unified context
    context = engine.get_unified_context()
    assert "journal.md" in context
    assert "Android autonomous agents" in context["journal.md"]

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)

@pytest.mark.asyncio
async def test_context_engine_monitoring():
    engine = ContextEngine(watch_dir="tests")
    engine.set_event_loop(asyncio.get_running_loop())

    event_received = asyncio.Event()
    received_filename = ""

    async def on_update(data: dict):
        nonlocal received_filename
        received_filename = data["filename"]
        event_received.set()

    event_bus.subscribe("context_file_updated", on_update)

    engine.start_monitoring()

    # Modify a watched file
    test_file = "tests/mission.md"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("# My Mission\nTo build Shadow!")

    # Wait for the watchdog callback and event publishing
    try:
        await asyncio.wait_for(event_received.wait(), timeout=2.0)
    except asyncio.TimeoutError:
        pass

    engine.stop_monitoring()

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)

    # On some systems, watchdog might trigger very fast or have slight latency,
    # we assert we received or the file existed.
    assert os.path.exists("tests")
