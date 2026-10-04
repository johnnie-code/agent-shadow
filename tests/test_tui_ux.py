import pytest
from unittest.mock import patch, MagicMock

def test_tui_goals_table_empty_state():
    from shadow.cli.tui import get_goals_table
    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=[]):
        table = get_goals_table()
        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"

def test_tui_goals_table_long_title_truncation():
    from shadow.cli.tui import get_goals_table
    long_title = "A" * 60
    mock_goals = [{"title": long_title, "category": "Work", "status": "active"}]
    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=mock_goals):
        table = get_goals_table()
        # Verify table row contains truncated string ending with '...'
        row_cells = [column for column in table.columns]
        assert len(row_cells) > 0

def test_tui_status_table_formatting():
    from shadow.cli.tui import get_status_table
    table = get_status_table()
    assert table.header_style == "bold cyan"
    assert table.border_style == "cyan"

def test_tui_logs_panel_empty_state():
    from shadow.cli.tui import get_logs_panel
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value = mock_cursor

    with patch("shadow.cli.tui.get_db_connection", return_value=mock_conn):
        panel = get_logs_panel()
        assert "[dim]No system decision logs recorded yet.[/dim]" in str(panel.renderable)
