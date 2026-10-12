import pytest
from unittest.mock import patch, MagicMock

def test_goals_table_empty_state():
    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=[]):
        from shadow.cli.tui import get_goals_table
        table = get_goals_table()
        assert len(table.rows) > 0

def test_goals_table_truncation():
    long_title = "A" * 50
    short_title = "Short Goal Title"
    mock_goals = [
        {"id": 1, "title": long_title, "category": "Work", "status": "active"},
        {"id": 2, "title": short_title, "category": "Health", "status": "completed"},
    ]
    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=mock_goals):
        from shadow.cli.tui import get_goals_table
        table = get_goals_table()
        assert len(table.rows) == 2
        # Check that long title is truncated with '...'
        assert long_title[:40] + "..." in table.columns[0]._cells[0]
        # Check that short title is not truncated
        assert short_title == table.columns[0]._cells[1]

def test_logs_panel_truncation_and_empty():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Case 1: Empty logs
    mock_cursor.fetchall.return_value = []
    with patch("shadow.cli.tui.get_db_connection", return_value=mock_conn):
        from shadow.cli.tui import get_logs_panel
        panel = get_logs_panel()
        assert "[dim]No system decision logs recorded yet.[/dim]" in panel.renderable

    # Case 2: Short and long log messages
    mock_cursor.fetchall.return_value = [
        {"level": "INFO", "action": "Short action", "created_at": "2026-10-12 12:00:00"},
        {"level": "ERROR", "action": "B" * 60, "created_at": "2026-10-12 12:01:00"}
    ]
    with patch("shadow.cli.tui.get_db_connection", return_value=mock_conn):
        from shadow.cli.tui import get_logs_panel
        panel = get_logs_panel()
        assert "Short action" in panel.renderable
        assert "Short action..." not in panel.renderable
        assert "B" * 55 + "..." in panel.renderable

def test_opportunities_panel_truncation():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchall.return_value = [
        {"title": "C" * 60, "category": "Remote", "url": "https://example.com"}
    ]
    with patch("shadow.cli.tui.get_db_connection", return_value=mock_conn):
        from shadow.cli.tui import get_opportunities_panel
        panel = get_opportunities_panel()
        assert "C" * 50 + "..." in panel.renderable
