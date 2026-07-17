import pytest
from shadow.core.database import init_db
from shadow.goals.engine import goals_engine

def test_goals_parsing():
    init_db()
    mock_markdown = """
# Identity
Elite Python Hacker.

# Long-Term Goals
- Secure a fully funded scholarship in Tokyo (depends on JLPT N2)
- Master local mobile AI quantization

# Current Projects
- PROJECT SHADOW agent harness

# Skills To Learn
- Advanced C++
"""
    goals = goals_engine.parse_mission_markdown(mock_markdown)
    assert len(goals) == 4

    # Assert specific goal characteristics
    g0 = goals[0]
    assert "Tokyo" in g0.title
    assert g0.category == "Long-Term Goals"
    assert g0.priority == "High"
    assert g0.dependencies == "JLPT N2"

    g3 = goals[3]
    assert g3.title == "Advanced C++"
    assert g3.category == "Skills To Learn"
    assert g3.priority == "Medium"

def test_goals_sync_db():
    init_db()

    mock_markdown = """
# Long-Term Goals
- Reach pass marks in Japanese N1
"""
    goals = goals_engine.parse_mission_markdown(mock_markdown)
    goals_engine.sync_goals_to_db(goals)

    active_goals = goals_engine.get_active_goals()
    assert len(active_goals) >= 1
    assert any("pass marks" in g["title"] for g in active_goals)
