import pytest
import asyncio
import os
from shadow.core.database import init_db, get_db_connection
from shadow.tools.registry import tool_registry
from shadow.goals.scanner import OpportunityScanner
from shadow.goals.generator import TaskGenerator
from shadow.goals.priority import priority_engine

@pytest.mark.asyncio
async def test_opportunity_scanner_and_generator():
    # Clear previous database to ensure clean isolated test run
    if os.path.exists("shadow.db"):
        os.remove("shadow.db")

    init_db()
    tool_registry.discover_tools()

    # 1. Scanner Test
    scanner = OpportunityScanner(provider_name="mock")
    opps = await scanner.scan(["Japan scholarships", "AI competitions"])
    assert len(opps) >= 1
    assert opps[0]["title"] == "MEXT Scholarship 2026"

    # Check insertion
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM opportunities ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    assert row is not None
    opp_id = row["id"]
    conn.close()

    # 2. Generator Test
    generator = TaskGenerator(provider_name="mock")
    tasks = await generator.generate_tasks_for_opportunity(opp_id)
    assert len(tasks) >= 1
    assert tasks[0]["title"] == "Read MEXT guidelines"

    # Check task insertion
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, status, priority_score FROM tasks WHERE opportunity_id = ?", (opp_id,))
    t_rows = cursor.fetchall()
    assert len(t_rows) >= 1
    assert t_rows[0]["status"] == "pending"
    conn.close()

def test_priority_engine():
    # Clear database to isolate
    if os.path.exists("shadow.db"):
        os.remove("shadow.db")

    # 1. Manual scoring formula test with expanded multi-factor priority
    score = priority_engine.calculate_priority_score(
        impact=9.0,
        urgency=8.0,
        confidence=0.9,
        difficulty=4.0,
        cost=2.0,
        time_required=4.0,
        alignment=9.5,
        roi=8.0,
        personal_growth=9.0,
        learning_value=8.5,
        risk=2.0
    )
    # 9.0*0.1 + 8.0*0.1 + (0.9*10)*0.1 + (11-4)*0.05 + (11-2)*0.05 + (11-4)*0.1 + 9.5*0.2 + 8.0*0.1 + 9.0*0.1 + 8.5*0.05 + (11-2)*0.05
    # = 0.9 + 0.8 + 0.9 + 0.35 + 0.45 + 0.7 + 1.9 + 0.8 + 0.9 + 0.425 + 0.45 = 8.575 -> 8.58
    assert score == 8.58

    # 2. Database reprioritization test
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    # Insert raw un-scored task
    cursor.execute("INSERT INTO tasks (title, description, category, status, priority_score) VALUES ('Read MEXT details', 'MEXT research info', 'Research', 'pending', 0.0)")
    conn.commit()
    conn.close()

    # Run dynamic re-priority
    priority_engine.reprioritize_all_tasks()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT priority_score FROM tasks WHERE title = 'Read MEXT details' LIMIT 1")
    p_score = cursor.fetchone()["priority_score"]
    conn.close()

    assert p_score > 5.0 # MEXT should get high priority boost
