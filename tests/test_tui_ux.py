import pytest
from unittest.mock import patch, MagicMock

def test_tui_get_goals_table_empty():
    from shadow.cli.tui import get_goals_table
    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=[]):
        table = get_goals_table()
        assert table.title == "Goals & Milestones Progress"
        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"
        assert len(table.columns) == 4
        assert table.columns[0].overflow == "ellipsis"
        assert table.columns[1].overflow == "ellipsis"
        assert table.columns[3].overflow == "ellipsis"
        assert len(table.rows) == 1

def test_tui_get_goals_table_populated():
    from shadow.cli.tui import get_goals_table
    mock_goals = [
        {"id": 1, "title": "Launch Shadow OS AI Companion", "category": "Product", "status": "active"},
        {"id": 2, "title": "Complete UX Accessibility Audit", "category": "Design", "status": "completed"}
    ]
    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=mock_goals):
        table = get_goals_table()
        assert table.title == "Goals & Milestones Progress"
        assert len(table.rows) == 2

def test_tui_get_status_table():
    from shadow.cli.tui import get_status_table
    table = get_status_table()
    assert table.title == "System & Android Capability Checklist"
    assert table.header_style == "bold cyan"
    assert table.border_style == "blue"
    assert table.columns[0].overflow == "ellipsis"
    assert table.columns[1].overflow == "ellipsis"
    assert table.columns[2].overflow == "ellipsis"
    assert len(table.rows) >= 6
