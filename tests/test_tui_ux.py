import pytest
from unittest.mock import patch, MagicMock
from rich.console import Console

def test_get_goals_table_empty():
    from shadow.cli.tui import get_goals_table

    with patch("shadow.cli.tui.goals_engine.get_active_goals") as mock_get_active:
        mock_get_active.return_value = []

        table = get_goals_table()

        # Verify custom table styles for high-contrast and ellipsis
        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"
        for col in table.columns:
            assert col.overflow == "ellipsis"

        # Verify empty state text with muted tags
        console = Console(color_system="standard")
        with console.capture() as capture:
            console.print(table)
        output = capture.get()
        assert "No active goals tracked" in output

def test_get_goals_table_with_active_goals():
    from shadow.cli.tui import get_goals_table

    mock_goals = [
        {"title": "Master Japanese N2", "category": "Languages", "status": "active"},
        {"title": "Finish Project Shadow", "category": "Development", "status": "completed"}
    ]

    with patch("shadow.cli.tui.goals_engine.get_active_goals") as mock_get_active:
        mock_get_active.return_value = mock_goals

        table = get_goals_table()

        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"

        console = Console(color_system="standard")
        with console.capture() as capture:
            console.print(table)
        output = capture.get()
        assert "Master Japanese N2" in output
        assert "Finish Project Shadow" in output

def test_get_status_table():
    from shadow.cli.tui import get_status_table

    with patch("shadow.cli.tui.get_db_connection") as mock_get_db:
        with patch("shadow.cli.tui.get_config") as mock_get_config:
            mock_conf = MagicMock()
            mock_conf.telegram_bot_token = "some_token"
            mock_conf.telegram_chat_id = "some_chat_id"
            mock_conf.default_provider = "mock"
            mock_get_config.return_value = mock_conf

            table = get_status_table()

            # Verify high-contrast header styling and border style
            assert table.header_style == "bold magenta"
            assert table.border_style == "cyan"
            for col in table.columns:
                assert col.overflow == "ellipsis"

            console = Console(color_system="standard")
            with console.capture() as capture:
                console.print(table)
            output = capture.get()
            assert "Background Daemon" in output
            assert "Telegram Companion" in output
