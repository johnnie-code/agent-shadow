import pytest
from unittest.mock import patch, MagicMock
from rich.table import Table
from rich.console import Console
from shadow.cli.tui import get_goals_table, get_status_table

@patch("shadow.cli.tui.goals_engine.get_active_goals")
def test_get_goals_table_styled(mock_get_active_goals):
    # Mock active goals returned as empty list to test empty state
    mock_get_active_goals.return_value = []

    table = get_goals_table()
    assert isinstance(table, Table)
    assert table.header_style == "bold magenta"
    assert table.border_style == "cyan"

    # Check that columns have overflow="ellipsis"
    for column in table.columns:
        assert column.overflow == "ellipsis"

    # Check the rendered console output
    console = Console()
    with console.capture() as capture:
        console.print(table)
    result = capture.get()
    assert "No active goals tracked" in result

@patch("shadow.cli.tui.get_db_connection")
@patch("shadow.cli.main.read_daemon_info")
def test_get_status_table_styled(mock_read_daemon, mock_get_db):
    # Mock database connections & daemon status to make check run cleanly
    mock_read_daemon.return_value = {"pid": 9999, "port": 8000}

    table = get_status_table()
    assert isinstance(table, Table)
    assert table.header_style == "bold magenta"
    assert table.border_style == "cyan"

    # Check that columns have overflow="ellipsis"
    for column in table.columns:
        assert column.overflow == "ellipsis"
