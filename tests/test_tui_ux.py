import pytest
from unittest.mock import patch, MagicMock


def test_get_goals_table_empty_state_and_styles():
    from shadow.cli.tui import get_goals_table

    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=[]):
        table = get_goals_table()
        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"
        assert len(table.columns) == 4
        for col in table.columns:
            assert col.overflow == "ellipsis"

        assert len(table.rows) == 1


def test_get_goals_table_with_items():
    from shadow.cli.tui import get_goals_table

    mock_goals = [
        {"title": "Learn Rust", "category": "Skill", "status": "active"},
        {"title": "Build OS", "category": "Project", "status": "completed"},
    ]
    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=mock_goals):
        table = get_goals_table()
        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"
        assert len(table.rows) == 2


def test_get_status_table_styles():
    from shadow.cli.tui import get_status_table

    table = get_status_table()
    assert table.header_style == "bold magenta"
    assert table.border_style == "cyan"
    assert len(table.columns) == 3
    for col in table.columns:
        assert col.overflow == "ellipsis"
