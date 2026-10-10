import pytest
from unittest.mock import patch, MagicMock

def test_tui_get_goals_table_empty_state():
    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=[]):
        from shadow.cli.tui import get_goals_table
        table = get_goals_table()
        assert table.title == "Goals & Milestones Progress"
        assert table.header_style == "bold magenta"
        cell_val = table.columns[0]._cells[0]
        assert "[dim]No goals tracked. Run 'shadow onboard' to define.[/dim]" in str(cell_val)
        assert "[dim]-[/dim]" in str(table.columns[1]._cells[0])

def test_tui_get_planner_panel_empty_state():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.side_effect = [
        {"count": 0},  # pending count
        {"count": 3},  # completed count
        None           # top_task_row
    ]

    with patch("shadow.cli.tui.get_db_connection", return_value=mock_conn):
        from shadow.cli.tui import get_planner_panel
        panel = get_planner_panel()
        assert panel.title == "📅 Daily Planner & Focus"
        assert "All caught up!" in panel.renderable

def test_tui_get_logs_panel_empty_state():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    with patch("shadow.cli.tui.get_db_connection", return_value=mock_conn):
        from shadow.cli.tui import get_logs_panel
        panel = get_logs_panel()
        assert panel.title == "📝 Dynamic Decision & Event Logs"
        assert "[dim]No system decision logs recorded yet.[/dim]" in panel.renderable
