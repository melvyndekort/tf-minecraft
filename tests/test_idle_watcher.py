"""Tests for idle watcher."""

from unittest.mock import MagicMock, patch

from minecraft_tools.idle_watcher.main import (
    get_player_count,
    get_service_status,
    scale_service,
)


class TestIdleWatcher:
    """Test idle watcher functionality."""

    @patch("minecraft_tools.idle_watcher.main.MCRcon")
    def test_get_player_count_success(self, mock_mcrcon):
        """Test successful player count retrieval."""
        mock_mcr = MagicMock()
        mock_mcr.command.return_value = (
            "There are 2 of a max of 20 players online: Player1, Player2"
        )
        mock_mcrcon.return_value.__enter__.return_value = mock_mcr

        count = get_player_count("localhost", 25575, "password")
        assert count == 2

    @patch("minecraft_tools.idle_watcher.main.MCRcon")
    def test_get_player_count_no_players(self, mock_mcrcon):
        """Test player count when no players online."""
        mock_mcr = MagicMock()
        mock_mcr.command.return_value = "There are 0 of a max of 20 players online:"
        mock_mcrcon.return_value.__enter__.return_value = mock_mcr

        count = get_player_count("localhost", 25575, "password")
        assert count == 0

    @patch("minecraft_tools.idle_watcher.main.MCRcon")
    def test_get_player_count_connection_error(self, mock_mcrcon):
        """Test player count when connection fails."""
        mock_mcrcon.side_effect = Exception("Connection refused")

        count = get_player_count("localhost", 25575, "password")
        assert count == -1

    @patch("minecraft_tools.idle_watcher.main.MCRcon")
    def test_get_player_count_invalid_response(self, mock_mcrcon):
        """Test player count with invalid response format."""
        mock_mcr = MagicMock()
        mock_mcr.command.return_value = "Invalid response format"
        mock_mcrcon.return_value.__enter__.return_value = mock_mcr

        count = get_player_count("localhost", 25575, "password")
        assert count == 0  # Returns 0 for invalid format, not -1

    def test_get_service_status_success(self):
        """Test successful service status retrieval."""
        mock_ecs = MagicMock()
        mock_ecs.describe_services.return_value = {
            "services": [{"desiredCount": 1, "runningCount": 1, "status": "ACTIVE"}]
        }

        status = get_service_status(mock_ecs, "test-cluster", "test-service")

        assert status["desired"] == 1
        assert status["running"] == 1

    def test_scale_service_success(self):
        """Test successful service scaling."""
        mock_ecs = MagicMock()

        result = scale_service(mock_ecs, "test-cluster", "test-service", 0)

        assert result is True
        mock_ecs.update_service.assert_called_once_with(
            cluster="test-cluster", service="test-service", desiredCount=0
        )

    def test_scale_service_failure(self):
        """Test service scaling failure."""
        mock_ecs = MagicMock()
        mock_ecs.update_service.side_effect = Exception("AWS Error")

        result = scale_service(mock_ecs, "test-cluster", "test-service", 0)

        assert result is False
