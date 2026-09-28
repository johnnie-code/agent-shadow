import pytest
from unittest.mock import patch

def test_get_goals_table_empty():
    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=[]):
        from shadow.cli.tui import get_goals_table
        table = get_goals_table()
        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"
        assert len(table.columns) == 4
        assert table.columns[0].overflow == "ellipsis"

        # Check rows for empty state
        assert len(table.rows) == 1

def test_get_goals_table_with_goals():
    mock_goals = [
        {"id": 1, "title": "Build Autonomous Shadow OS TUI", "category": "Development", "status": "active"},
        {"id": 2, "title": "Achieve 100% UX Excellence", "category": "Quality", "status": "completed"}
    ]
    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=mock_goals):
        from shadow.cli.tui import get_goals_table
        table = get_goals_table()
        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"
        assert len(table.columns) == 4
        assert table.columns[0].overflow == "ellipsis"
        assert len(table.rows) == 2
