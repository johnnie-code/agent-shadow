import pytest
import asyncio
import os
from shadow.core.database import init_db, get_db_connection
from shadow.goals.engine import goals_engine
from shadow.goals.scanner import OpportunityScanner
from shadow.goals.generator import TaskGenerator
from shadow.goals.priority import priority_engine
from shadow.goals.executor import execution_engine
from shadow.goals.reflection import reflection_engine

@pytest.mark.asyncio
async def test_full_autonomous_loop():
    # 1. Clean previous database if exists to ensure clean isolated test run
    if os.path.exists("shadow.db"):
        os.remove("shadow.db")

    init_db()

    # 2. Parse mock mission and sync goals
    mock_mission = """
# Long-Term Goals
- Master Japanese JLPT N1
- Win Tokyo AI Hackathon
"""
    parsed_goals = goals_engine.parse_mission_markdown(mock_mission)
    goals_engine.sync_goals_to_db(parsed_goals)

    active_goals = goals_engine.get_active_goals()
    assert len(active_goals) == 2

    # 3. Scan for matching opportunities
    scanner = OpportunityScanner()
    opps = await scanner.scan(["Japan JLPT N1 studies", "Tokyo hackathons"])
    assert len(opps) >= 1

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM opportunities WHERE status = 'new'")
    new_opp_row = cursor.fetchone()
    assert new_opp_row is not None
    opp_id = new_opp_row["id"]
    conn.close()

    # 4. Generate Action Tasks
    generator = TaskGenerator()
    tasks = await generator.generate_tasks_for_opportunity(opp_id)
    assert len(tasks) >= 1

    # 5. Prioritize Tasks
    priority_engine.reprioritize_all_tasks()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, status, priority_score, safety_level FROM tasks WHERE opportunity_id = ?", (opp_id,))
    task_rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    assert len(task_rows) >= 1
    assert task_rows[0]["status"] == "pending"
    assert task_rows[0]["priority_score"] > 0.0

    # 6. Execute Task Safely
    task_to_run = task_rows[0]
    res = await execution_engine.execute_task(task_to_run["id"])

    if task_to_run["safety_level"] < 2:
        assert res["success"] is True
    else:
        assert res["success"] is False
        assert res["status"] == "pending_approval"

    # 7. Strategic Evening Reflection Audit
    reflection_report = await reflection_engine.perform_daily_reflection()
    assert len(reflection_report) > 0
    assert "Error" not in reflection_report
