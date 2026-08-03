from unittest.mock import patch, MagicMock


def test_tui_get_status_table():
    from shadow.cli.tui import get_status_table
    # Patch dependencies in the shadow.cli.main namespace since they are imported locally inside the function
    with patch("shadow.cli.main.read_daemon_info") as mock_daemon_info, \
         patch("shadow.cli.main.is_pid_running") as mock_pid_running:

        mock_daemon_info.return_value = {"pid": 1234, "port": 8000}
        mock_pid_running.return_value = True

        table = get_status_table()

        # Check table border style
        assert table.border_style == "cyan"

        # Check column properties
        for column in table.columns:
            assert column.header_style == "bold magenta"
            assert column.overflow == "ellipsis"

        # Check subsystems are rendered
        subsystems = [row for row in table.columns[0]._cells]
        assert "Background Daemon" in subsystems
        assert "Telegram Companion" in subsystems


def test_tui_get_goals_table_empty():
    from shadow.cli.tui import get_goals_table
    # Patch get_active_goals under the shadow.cli.tui namespace
    with patch("shadow.cli.tui.goals_engine.get_active_goals") as mock_get_active:
        mock_get_active.return_value = []

        table = get_goals_table()

        # Check table border style
        assert table.border_style == "cyan"

        # Check column properties
        for column in table.columns:
            assert column.header_style == "bold magenta"
            assert column.overflow == "ellipsis"

        # Check empty state message row cells
        # The row is added as the empty state.
        row_cells = [cell for cell in table.columns[0]._cells]
        assert "[dim]No goals tracked. Run 'shadow onboard' to define.[/dim]" in row_cells


def test_tui_get_goals_table_with_active_goals():
    from shadow.cli.tui import get_goals_table
    # Patch get_active_goals under the shadow.cli.tui namespace
    with patch("shadow.cli.tui.goals_engine.get_active_goals") as mock_get_active:
        mock_get_active.return_value = [
            {"title": "Build Shadow OS TUI", "category": "Development", "status": "active"},
            {"title": "Deploy Android App", "category": "Release", "status": "completed"},
        ]

        table = get_goals_table()

        assert table.border_style == "cyan"

        # Check column properties
        for column in table.columns:
            assert column.header_style == "bold magenta"
            assert column.overflow == "ellipsis"

        # Check rendered titles
        goal_titles = [cell for cell in table.columns[0]._cells]
        assert "Build Shadow OS TUI" in goal_titles
        assert "Deploy Android App" in goal_titles
