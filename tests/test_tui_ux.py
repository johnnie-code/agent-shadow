import pytest
from unittest.mock import patch, MagicMock
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout

def test_make_layout():
    from shadow.cli.tui import make_layout
    layout = make_layout()
    assert isinstance(layout, Layout)
    assert layout.get("header") is not None
    assert layout.get("body") is not None
    assert layout.get("footer") is not None

def test_get_header():
    from shadow.cli.tui import get_header
    header = get_header()
    assert isinstance(header, Panel)
    assert "SHADOW AUTONOMOUS OS" in str(header.renderable)

def test_get_footer():
    from shadow.cli.tui import get_footer
    footer = get_footer()
    assert isinstance(footer, Panel)
    assert "Ctrl+C to Exit" in str(footer.renderable)

def test_get_mission_panel():
    from shadow.cli.tui import get_mission_panel
    panel = get_mission_panel()
    assert isinstance(panel, Panel)
    assert panel.title == "🎯 Active Life Mission & Profile"

@patch("shadow.cli.tui.goals_engine.get_active_goals")
def test_get_goals_table_empty(mock_get_active_goals):
    mock_get_active_goals.return_value = []
    from shadow.cli.tui import get_goals_table
    table = get_goals_table()
    assert isinstance(table, Table)
    assert table.border_style == "cyan"
    assert table.columns[0].header_style == "bold magenta"

    cells = table.columns[0]._cells
    assert len(cells) == 1
    assert "No goals tracked." in cells[0]
    assert "shadow onboard" in cells[0]

@patch("shadow.cli.tui.goals_engine.get_active_goals")
def test_get_goals_table_with_active(mock_get_active_goals):
    mock_get_active_goals.return_value = [
        {"title": "Climb Fuji", "category": "Personal", "status": "active"},
        {"title": "Pass N2", "category": "Language", "status": "completed"},
    ]
    from shadow.cli.tui import get_goals_table
    table = get_goals_table()
    assert isinstance(table, Table)
    assert table.columns[0].overflow == "ellipsis"
    assert len(table.rows) == 2

@patch("shadow.cli.tui.get_db_connection")
def test_get_opportunities_panel_empty(mock_get_db):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value = mock_cursor
    mock_get_db.return_value = mock_conn

    from shadow.cli.tui import get_opportunities_panel
    panel = get_opportunities_panel()
    assert isinstance(panel, Panel)
    assert "No new opportunities found yet" in str(panel.renderable)

@patch("shadow.cli.tui.get_db_connection")
def test_get_opportunities_panel_with_data(mock_get_db):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {"title": "Found startup!", "category": "Work", "url": "http://example.com"}
    ]
    mock_conn.cursor.return_value = mock_cursor
    mock_get_db.return_value = mock_conn

    from shadow.cli.tui import get_opportunities_panel
    panel = get_opportunities_panel()
    assert isinstance(panel, Panel)
    assert "Found startup!" in str(panel.renderable)

@patch("shadow.cli.tui.get_db_connection")
def test_get_planner_panel(mock_get_db):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        {"count": 3},  # pending
        {"count": 5},  # completed
        {"title": "Master pytest"}  # top task
    ]
    mock_conn.cursor.return_value = mock_cursor
    mock_get_db.return_value = mock_conn

    from shadow.cli.tui import get_planner_panel
    panel = get_planner_panel()
    assert isinstance(panel, Panel)
    assert "3 tasks" in str(panel.renderable)
    assert "Master pytest" in str(panel.renderable)

def test_get_status_table():
    with patch("shadow.cli.main.read_daemon_info") as mock_read, \
         patch("shadow.cli.main.is_pid_running") as mock_running:
        mock_read.return_value = {"pid": 1234, "port": 8000}
        mock_running.return_value = True

        from shadow.cli.tui import get_status_table
        table = get_status_table()
        assert isinstance(table, Table)
        assert table.border_style == "cyan"
        assert table.columns[0].header_style == "bold magenta"
        assert table.columns[0].overflow == "ellipsis"

@patch("shadow.cli.tui.get_db_connection")
def test_get_logs_panel_empty(mock_get_db):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value = mock_cursor
    mock_get_db.return_value = mock_conn

    from shadow.cli.tui import get_logs_panel
    panel = get_logs_panel()
    assert isinstance(panel, Panel)
    assert "[dim]No system decision logs recorded yet.[/dim]" in str(panel.renderable)

@patch("shadow.cli.tui.get_db_connection")
def test_get_logs_panel_with_data(mock_get_db):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {"level": "INFO", "action": "Did something", "created_at": "2026-08-10 12:00:00"}
    ]
    mock_conn.cursor.return_value = mock_cursor
    mock_get_db.return_value = mock_conn

    from shadow.cli.tui import get_logs_panel
    panel = get_logs_panel()
    assert isinstance(panel, Panel)
    assert "Did something" in str(panel.renderable)
