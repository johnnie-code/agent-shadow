import pytest
from unittest.mock import patch, MagicMock

def test_tui_goals_table_empty_state_and_styles():
    with patch("shadow.cli.tui.goals_engine.get_active_goals") as mock_get_goals:
        mock_get_goals.return_value = []
        from shadow.cli.tui import get_goals_table
        table = get_goals_table()

        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"
        assert len(table.columns) == 4
        assert table.columns[0].overflow == "ellipsis"
        assert table.columns[1].overflow == "ellipsis"

        # Check row count
        assert len(table.rows) == 1

def test_tui_goals_table_with_active_goals():
    sample_goals = [
        {"title": "Build Autonomous AI OS", "category": "Tech", "status": "active"},
        {"title": "Deploy Android Companion App", "category": "Mobile", "status": "completed"}
    ]
    with patch("shadow.cli.tui.goals_engine.get_active_goals") as mock_get_goals:
        mock_get_goals.return_value = sample_goals
        from shadow.cli.tui import get_goals_table
        table = get_goals_table()

        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"
        assert len(table.rows) == 2

def test_tui_status_table_styles():
    from shadow.cli.tui import get_status_table
    table = get_status_table()

    assert table.header_style == "bold magenta"
    assert table.border_style == "cyan"
    assert len(table.columns) == 3
    for col in table.columns:
        assert col.overflow == "ellipsis"
    assert len(table.rows) == 6
