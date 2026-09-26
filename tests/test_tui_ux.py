from unittest.mock import patch
import pytest
from rich.table import Table

def test_goals_table_empty_state_placeholders():
    from shadow.cli.tui import get_goals_table
    with patch("shadow.cli.tui.goals_engine.get_active_goals", return_value=[]):
        table = get_goals_table()
        assert isinstance(table, Table)
        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"
        assert len(table.columns) == 4
        for col in table.columns:
            assert col.overflow == "ellipsis"

        # Verify empty state row values contain dim styling placeholders
        assert len(table.columns[0]._cells) == 1
        assert "No goals tracked" in str(table.columns[0]._cells[0])
        assert "N/A" in str(table.columns[1]._cells[0])
        assert "[□□□□□□□□□□] 0%" in str(table.columns[2]._cells[0])
        assert "INACTIVE" in str(table.columns[3]._cells[0])

def test_status_table_styling_and_overflow():
    from shadow.cli.tui import get_status_table
    with patch("shadow.cli.main.read_daemon_info", return_value=None):
        table = get_status_table()
        assert isinstance(table, Table)
        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"
        assert len(table.columns) == 3
        for col in table.columns:
            assert col.overflow == "ellipsis"
