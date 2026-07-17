import pytest
from shadow.core.database import init_db
from shadow.memory.memory import memory_engine

def test_sqlite_memory_engine_original():
    """
    Ensure existing tests for backward compatibility continue to pass perfectly.
    """
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


def test_memory_engine_crud_milestone1():
    """
    Verify complete save, search, update, and delete APIs.
    """
    init_db()

    # 1. Save memory
    mem_id = memory_engine.save_memory(
        category="project",
        content="Implementing Persistent Memory for Milestone 1 in Project Shadow.",
        key="milestone_1_mem",
        tags=["milestone1", "persistent", "memory"],
        importance_level="Permanent",
        workspace="workspace_a"
    )
    assert mem_id > 0

    # Retrieve by key
    retrieved = memory_engine.get_memory_by_key("milestone_1_mem")
    assert retrieved is not None
    assert retrieved["id"] == mem_id
    assert retrieved["category"] == "project"
    assert retrieved["workspace"] == "workspace_a"
    assert "milestone1" in retrieved["tags"]

    # 2. Search memory (with workspace filter)
    # Inside workspace_a, we should see both workspace_a and global memories
    results_a = memory_engine.search_memory("Persistent", workspace="workspace_a")
    assert len(results_a) >= 1
    assert any(r["id"] == mem_id for r in results_a)

    # In workspace_b, we should NOT see workspace_a memories
    results_b = memory_engine.search_memory("Persistent", workspace="workspace_b")
    assert not any(r["id"] == mem_id for r in results_b)

    # 3. Update memory
    success = memory_engine.update_memory(
        mem_id,
        content="Updated Persistent Memory for Milestone 1.",
        importance_score=9.8,
        workspace="global"
    )
    assert success is True

    updated = memory_engine.get_memory_by_key("milestone_1_mem")
    assert updated["content"] == "Updated Persistent Memory for Milestone 1."
    assert updated["importance_score"] == 9.8
    assert updated["workspace"] == "global"

    # Now that it is global, workspace_b should be able to see it!
    results_b_post_update = memory_engine.search_memory("Persistent", workspace="workspace_b")
    assert any(r["id"] == mem_id for r in results_b_post_update)

    # 4. Delete memory
    del_success = memory_engine.delete_memory(mem_id)
    assert del_success is True

    deleted = memory_engine.get_memory_by_key("milestone_1_mem")
    assert deleted is None


def test_memory_importance_heuristics():
    """
    Test memory scoring and importance heuristics.
    """
    init_db()

    # Scoring check with keywords like 'mission' or 'goal' or tags like 'critical'
    id_1 = memory_engine.save_memory(
        category="note",
        content="A casual developer note about standard formatting.",
        tags=["standard"]
    )
    m1 = memory_engine.search_memory("developer note")[0]

    id_2 = memory_engine.save_memory(
        category="note",
        content="Our primary mission is to build the ultimate chief of staff OS.",
        tags=["critical", "mission"]
    )
    m2 = memory_engine.search_memory("ultimate chief")[0]

    # m2 content and tags have high-value terms, so its score should be significantly higher
    assert m2["importance_score"] > m1["importance_score"]

    memory_engine.delete_memory(id_1)
    memory_engine.delete_memory(id_2)


def test_memory_summarization():
    """
    Test semantic memory summarization.
    """
    init_db()

    # Insert some memories to summarize
    id_1 = memory_engine.save_memory(
        category="architecture",
        content="The system is structured as a hub-and-spoke with SQLite as the brain.",
        tags=["architecture", "sqlite"],
        workspace="ws_summary"
    )
    id_2 = memory_engine.save_memory(
        category="style",
        content="Python code must adhere to clean guidelines, utilizing typed arguments.",
        tags=["style", "guidelines"],
        workspace="ws_summary"
    )

    # Summarize memories scoped to 'ws_summary'
    summary = memory_engine.summarize_memory(workspace="ws_summary")
    assert "Mock" in summary or "Deterministic" in summary or "Summary" in summary

    # Clean up
    memory_engine.delete_memory(id_1)
    memory_engine.delete_memory(id_2)
