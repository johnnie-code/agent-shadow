import pytest
from shadow.core.database import init_db
from shadow.memory.memory import memory_engine

def test_sqlite_memory_engine():
    # Make sure DB tables exist
    init_db()

    # Add preference memory
    memory_engine.add_memory(
        category="preference",
        content="User prefers high-impact software engineering hacks over slow research.",
        key="working_style",
        tags=["style", "coding"]
    )

    # Retrieve preference by key
    retrieved = memory_engine.get_memory_by_key("working_style")
    assert retrieved is not None
    assert retrieved["category"] == "preference"
    assert "high-impact" in retrieved["content"]

    # Keyword search
    search_results = memory_engine.search_memories("hacks")
    assert len(search_results) >= 1
    assert search_results[0]["key"] == "working_style"

    # Test conversation history insertion and fetch
    sess_id = "test_session_123"
    memory_engine.add_conversation_message(
        session_id=sess_id,
        role="user",
        content="How do I setup my MEXT Scholarship target?",
        provider="mock",
        tokens=10,
        cost=0.0
    )

    history = memory_engine.get_conversation_history(sess_id)
    assert len(history) == 1
    assert history[0]["role"] == "user"
    assert "MEXT" in history[0]["content"]

    memory_engine.clear_conversation(sess_id)
    assert len(memory_engine.get_conversation_history(sess_id)) == 0
