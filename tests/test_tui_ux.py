import pytest
from unittest.mock import patch, MagicMock

@patch("shadow.cli.tui.goals_engine.get_active_goals")
def test_goals_table_empty_state(mock_get_goals):
    # Setup empty goals
    mock_get_goals.return_value = []

    # Import locally to avoid module reference desynchronization
    from shadow.cli.tui import get_goals_table

    table = get_goals_table()

    assert table.title == "Goals & Milestones Progress"
    assert table.header_style == "bold magenta"
    assert table.border_style == "cyan"

    # Verify we have styled columns with overflow="ellipsis"
    cols = table.columns
    assert len(cols) == 4
    assert cols[0].overflow == "ellipsis"
    assert cols[1].overflow == "ellipsis"
    assert cols[3].overflow == "ellipsis"

    # Verify empty state row values with [dim] tags
    cells = [cell for cell in table.columns[0].cells]
    assert "[dim]No active goals found" in cells[0]

@patch("shadow.cli.tui.goals_engine.get_active_goals")
def test_goals_table_with_data(mock_get_goals):
    # Setup goals
    mock_get_goals.return_value = [
        {"id": 1, "title": "Implement Micro-UX", "category": "UX", "status": "active"},
        {"id": 2, "title": "Write Unit Tests", "category": "QA", "status": "completed"}
    ]

    from shadow.cli.tui import get_goals_table
    table = get_goals_table()

    assert table.title == "Goals & Milestones Progress"
    cols = table.columns
    assert len(cols) == 4

    # Verify rows are populated
    cells_first = [cell for cell in table.columns[0].cells]
    assert len(cells_first) == 2
    assert "Implement Micro-UX" in cells_first[0]
    assert "Write Unit Tests" in cells_first[1]

@patch("shadow.cli.main.is_pid_running")
@patch("shadow.cli.main.read_daemon_info")
def test_status_table_rendering(mock_read_info, mock_is_pid):
    mock_read_info.return_value = {"pid": 1234, "port": 8000}
    mock_is_pid.return_value = True

    from shadow.cli.tui import get_status_table
    table = get_status_table()

    assert table.title == "System & Android Capability Checklist"
    assert table.header_style == "bold cyan"
    assert table.border_style == "magenta"

    cols = table.columns
    assert len(cols) == 3
    assert cols[0].overflow == "ellipsis"
    assert cols[1].overflow == "ellipsis"
    assert cols[2].overflow == "ellipsis"

    # Check some content
    subsystems = [cell for cell in table.columns[0].cells]
    assert "Background Daemon" in subsystems
    assert "SQLite Database" in subsystems
