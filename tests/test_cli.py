"""Tests for CLI argument parsing and command dispatch."""

from unittest.mock import MagicMock, patch

import pytest

from artemis_calendar.cli import cmd_status, main


class TestCmdStatus:
    @patch("artemis_calendar.cli.get_connection")
    @patch("artemis_calendar.cli.apply_migrations")
    def test_status_prints_table_counts(self, mock_migrations, mock_conn, capsys):
        conn = MagicMock()
        mock_conn.return_value = conn
        conn.execute.return_value.fetchall.side_effect = [
            [("dim_image",), ("dim_category",)],  # table list
            [(100,)],  # dim_category count
            [(12000,)],  # dim_image count
        ]
        conn.execute.return_value.fetchone.side_effect = [100, 12000]

        ns = MagicMock()
        cmd_status(ns)

        conn.close.assert_called_once()


class TestMainParser:
    def test_help_exits_cleanly(self):
        with (
            pytest.raises(SystemExit) as exc_info,
            patch("sys.argv", ["artemis-pipeline", "--help"]),
        ):
            main()
        assert exc_info.value.code == 0

    def test_no_command_exits_1(self):
        with (
            pytest.raises(SystemExit) as exc_info,
            patch("sys.argv", ["artemis-pipeline"]),
        ):
            main()
        assert exc_info.value.code == 1

    def test_migrate_dispatches(self):
        with (
            patch("sys.argv", ["artemis-pipeline", "migrate"]),
            patch("artemis_calendar.cli.cmd_migrate") as mock_cmd,
        ):
            main()
            mock_cmd.assert_called_once()

    def test_status_dispatches(self):
        with (
            patch("sys.argv", ["artemis-pipeline", "status"]),
            patch("artemis_calendar.cli.cmd_status") as mock_cmd,
        ):
            main()
            mock_cmd.assert_called_once()
