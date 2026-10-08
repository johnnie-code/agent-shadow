import io
from unittest.mock import patch
from rich.console import Console

def test_goals_table_empty_state_and_formatting():
    from shadow.cli.tui import get_goals_table

    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=[]):
        table = get_goals_table()
        assert table.header_style == "bold magenta"
        assert len(table.columns) == 4
        assert all(col.overflow == "ellipsis" for col in table.columns)
        assert table.columns[0]._cells[0] == "[dim]No goals tracked. Run 'shadow onboard' to define.[/dim]"
        assert table.columns[1]._cells[0] == "[dim]N/A[/dim]"
        assert table.columns[2]._cells[0] == "[dim]N/A[/dim]"
        assert table.columns[3]._cells[0] == "[dim]INACTIVE[/dim]"

def test_goals_table_with_active_goals():
    from shadow.cli.tui import get_goals_table

    mock_goals = [
        {"id": 1, "title": "Build AI Agent OS", "category": "Engineering", "status": "active"},
        {"id": 2, "title": "Launch Mobile App", "category": "Product", "status": "completed"},
    ]

    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=mock_goals):
        table = get_goals_table()
        assert table.columns[0]._cells[0] == "Build AI Agent OS"
        assert table.columns[1]._cells[0] == "Engineering"
        assert "40%" in table.columns[2]._cells[0]
        assert table.columns[3]._cells[0] == "ACTIVE"

def test_status_table_formatting():
    from shadow.cli.tui import get_status_table

    table = get_status_table()
    assert table.header_style == "bold cyan"
    assert len(table.columns) == 3
    assert all(col.overflow == "ellipsis" for col in table.columns)
    assert len(table.columns[0]._cells) >= 5
