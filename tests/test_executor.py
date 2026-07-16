import pytest
from shadow.core.database import init_db, get_db_connection
from shadow.goals.executor import execution_engine

@pytest.mark.asyncio
async def test_execution_safety_levels():
    init_db()

    # 1. Level 0 task: safe/auto
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (title, description, category, safety_level, status)
        VALUES ('Search scholarships', 'Looking up Tokyo universities', 'Research', 0, 'pending')
    """)
    t0_id = cursor.lastrowid
    conn.commit()
    conn.close()

    res = await execution_engine.execute_task(t0_id)
    assert res["success"] is True

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM tasks WHERE id = ?", (t0_id,))
    assert cursor.fetchone()["status"] == "completed"
    conn.close()

    # 2. Level 2 task: requires approval
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (title, description, category, safety_level, status)
        VALUES ('Deploy code', 'Push changes to production remote', 'Coding', 2, 'pending')
    """)
    t2_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # First execution attempt should pause on Level 2 and block
    res_l2 = await execution_engine.execute_task(t2_id)
    assert res_l2["success"] is False
    assert res_l2["status"] == "pending_approval"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, status FROM approvals WHERE task_id = ?", (t2_id,))
    app_row = cursor.fetchone()
    assert app_row is not None
    assert app_row["status"] == "pending"
    app_id = app_row["id"]
    conn.close()

    # Process Approval
    execution_engine.process_approval(app_id, approved=True, reason="Valid deployment path")

    # Execute Task again
    res_approved = await execution_engine.execute_task(t2_id)
    assert res_approved["success"] is True

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM tasks WHERE id = ?", (t2_id,))
    assert cursor.fetchone()["status"] == "completed"
    conn.close()
