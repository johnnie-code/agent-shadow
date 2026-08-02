from unittest.mock import patch, MagicMock
from rich.table import Table
from rich.panel import Panel
from shadow.cli.tui import get_goals_table, get_status_table, get_logs_panel

def test_get_goals_table_empty():
    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=[]):
        table = get_goals_table()
        assert isinstance(table, Table)
        assert table.title == "Goals & Milestones Progress"
        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"

        # Check overflow ellipsis on columns
        for col in table.columns:
            if col.header != "Progress Bar":
                assert col.overflow == "ellipsis"

        # Verify polished empty state row is added with dim styling
        cells = [table.columns[i]._cells[0] for i in range(len(table.columns))]
        assert "[dim]No active goals[/dim]" in cells
        assert "[dim]N/A[/dim]" in cells


def test_get_goals_table_with_items():
    mock_goals = [
        {"title": "Goal A", "category": "Work", "status": "active"},
        {"title": "Goal B", "category": "Learning", "status": "completed"}
    ]
    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=mock_goals):
        table = get_goals_table()
        assert isinstance(table, Table)
        assert len(table.rows) == 2

        # Verify cells have original values
        cells_g1 = [table.columns[i]._cells[0] for i in range(len(table.columns))]
        assert "Goal A" in cells_g1
        assert "Work" in cells_g1


def test_get_status_table():
    with patch("shadow.cli.main.read_daemon_info", return_value=None), \
         patch("shadow.cli.main.is_pid_running", return_value=False):
        table = get_status_table()
        assert isinstance(table, Table)
        assert table.title == "System & Android Capability Checklist"
        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"

        for col in table.columns:
            assert col.overflow == "ellipsis"


def test_get_logs_panel_empty():
    # Mock database to return empty logs list
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value = mock_cursor

    with patch("shadow.cli.tui.get_db_connection", return_value=mock_conn):
        panel = get_logs_panel()
        assert isinstance(panel, Panel)
        assert "[dim]No system decision logs recorded yet.[/dim]" in panel.renderable
