import pytest
from unittest.mock import patch, MagicMock

def test_goals_table_empty_state_and_styles():
    with patch("shadow.cli.tui.goals_engine.get_active_goals") as mock_goals:
        mock_goals.return_value = []
        from shadow.cli.tui import get_goals_table
        table = get_goals_table()
        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"
        assert len(table.columns) == 4
        assert table.columns[0].overflow == "ellipsis"
        assert table.columns[1].overflow == "ellipsis"
        assert table.columns[3].overflow == "ellipsis"

def test_status_table_styles_and_columns():
    with patch("shadow.cli.tui.get_config") as mock_cfg, \
         patch("shadow.cli.main.read_daemon_info", return_value=None):
        mock_config = MagicMock()
        mock_config.telegram_bot_token = None
        mock_config.telegram_chat_id = None
        mock_config.default_provider = "mock"
        mock_cfg.return_value = mock_config

        from shadow.cli.tui import get_status_table
        table = get_status_table()
        assert table.header_style == "bold magenta"
        assert table.border_style == "cyan"
        assert len(table.columns) == 3
        assert table.columns[0].overflow == "ellipsis"
        assert table.columns[1].overflow == "ellipsis"
        assert table.columns[2].overflow == "ellipsis"

def test_logs_panel_empty_state():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value = mock_cursor

    with patch("shadow.cli.tui.get_db_connection", return_value=mock_conn):
        from shadow.cli.tui import get_logs_panel
        panel = get_logs_panel()
        assert "[dim]No system decision logs recorded yet.[/dim]" in str(panel.renderable)
