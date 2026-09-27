import pytest
from unittest.mock import patch, MagicMock

def test_tui_goals_table_empty_state():
    from shadow.cli.tui import get_goals_table
    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=[]):
        table = get_goals_table()
        assert table.title == "Goals & Milestones Progress"
        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"
        assert len(table.columns) == 4
        assert table.columns[0].overflow == "ellipsis"
        assert table.columns[1].overflow == "ellipsis"
        assert len(table.rows) == 1

def test_tui_goals_table_with_data():
    from shadow.cli.tui import get_goals_table
    mock_goals = [
        {"title": "Launch Shadow OS", "category": "Product", "status": "active"}
    ]
    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=mock_goals):
        table = get_goals_table()
        assert len(table.rows) == 1

def test_tui_status_table_styling():
    from shadow.cli.tui import get_status_table
    with patch("shadow.cli.main.read_daemon_info", return_value=None):
        table = get_status_table()
        assert table.title == "System & Android Capability Checklist"
        assert table.header_style == "bold cyan"
        assert table.border_style == "cyan"
        assert table.columns[0].overflow == "ellipsis"
        assert table.columns[2].overflow == "ellipsis"
