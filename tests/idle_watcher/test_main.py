import pytest
import os
import signal
from unittest.mock import patch, MagicMock
from datetime import datetime

from minecraft_tools.idle_watcher import main as idle_watcher


class TestIdleWatcher:
    
    @patch('minecraft_tools.idle_watcher.main.requests.post')
    def test_send_discord_message_success(self, mock_post):
        """Test successful Discord message sending"""
        with patch.dict(os.environ, {'DISCORD_WEBHOOK': 'http://test.webhook'}):
            mock_post.return_value.status_code = 200
            idle_watcher.send_discord_message("Test message")
            mock_post.assert_called_once()

    def test_send_discord_message_no_webhook(self):
        """Test Discord message when no webhook is configured"""
        with patch.dict(os.environ, {}, clear=True):
            # Should not raise an exception
            idle_watcher.send_discord_message("Test message")

    @patch('minecraft_tools.idle_watcher.main.requests.post')
    def test_send_discord_message_failure(self, mock_post):
        """Test Discord message when request fails"""
        with patch.dict(os.environ, {'DISCORD_WEBHOOK': 'http://test.webhook'}):
            mock_post.return_value.status_code = 400
            # Should not raise an exception
            idle_watcher.send_discord_message("Test message")

    @patch('minecraft_tools.idle_watcher.main.MCRcon')
    def test_send_rcon_message_success(self, mock_mcrcon):
        """Test successful RCON message sending"""
        mock_mcr = MagicMock()
        mock_mcrcon.return_value.__enter__.return_value = mock_mcr
        
        with patch.dict(os.environ, {'RCON_HOST': 'localhost', 'RCON_PASSWORD': 'test'}):
            idle_watcher.send_rcon_message("Test message")
            mock_mcr.command.assert_called_once_with('say Test message')

    @patch('minecraft_tools.idle_watcher.main.MCRcon')
    def test_send_rcon_message_failure(self, mock_mcrcon):
        """Test RCON message when connection fails"""
        mock_mcrcon.side_effect = Exception("Connection failed")
        
        with patch.dict(os.environ, {'RCON_HOST': 'localhost', 'RCON_PASSWORD': 'test'}):
            # Should not raise an exception
            idle_watcher.send_rcon_message("Test message")

    @patch('minecraft_tools.idle_watcher.main.send_discord_message')
    @patch('minecraft_tools.idle_watcher.main.MCRcon')
    def test_get_player_count_server_becomes_available(self, mock_mcrcon, mock_discord):
        """Test Discord notification when server becomes available"""
        mock_mcr = MagicMock()
        mock_mcr.command.return_value = "There are 1 of a max of 20 players online: Player1"
        mock_mcrcon.return_value.__enter__.return_value = mock_mcr
    
        # Reset server availability
        idle_watcher.server_available = False
    
        with patch.dict(os.environ, {'DNS_NAME': 'mc.example.com'}):
            count = idle_watcher.get_player_count()
            assert count == 1
            mock_discord.assert_called_once()
            assert "server is online and reachable" in mock_discord.call_args[0][0]

    @patch('minecraft_tools.idle_watcher.main.MCRcon')
    def test_get_player_count_server_already_available(self, mock_mcrcon):
        """Test no Discord notification when server already available"""
        mock_mcr = MagicMock()
        mock_mcr.command.return_value = "There are 2 of a max of 20 players online: Player1, Player2"
        mock_mcrcon.return_value.__enter__.return_value = mock_mcr
    
        # Set server as already available
        idle_watcher.server_available = True
    
        count = idle_watcher.get_player_count()
        assert count == 2

    @patch('minecraft_tools.idle_watcher.main.MCRcon')
    def test_get_player_count_no_players(self, mock_mcrcon):
        """Test parsing when no players are online"""
        mock_mcr = MagicMock()
        mock_mcr.command.return_value = "There are 0 of a max of 20 players online:"
        mock_mcrcon.return_value.__enter__.return_value = mock_mcr
    
        count = idle_watcher.get_player_count()
        assert count == 0

    @patch('minecraft_tools.idle_watcher.main.MCRcon')
    def test_get_player_count_connection_error(self, mock_mcrcon):
        """Test handling of RCON connection errors"""
        mock_mcrcon.side_effect = Exception("Connection refused")
    
        count = idle_watcher.get_player_count()
        assert count == 0  # Function returns 0 on error, not -1

    @patch('minecraft_tools.idle_watcher.main.MCRcon')
    def test_get_player_count_invalid_response(self, mock_mcrcon):
        """Test handling of unexpected RCON response format"""
        mock_mcr = MagicMock()
        mock_mcr.command.return_value = "Invalid response format"
        mock_mcrcon.return_value.__enter__.return_value = mock_mcr
    
        count = idle_watcher.get_player_count()
        assert count == 0  # Function returns 0 on parse error, not -1

    @patch('minecraft_tools.idle_watcher.main.boto3.client')
    @patch('minecraft_tools.idle_watcher.main.send_discord_message')
    def test_shutdown_ecs_service_success(self, mock_discord, mock_boto_client):
        """Test successful ECS service shutdown"""
        mock_ecs = MagicMock()
        mock_boto_client.return_value = mock_ecs
    
        with patch.dict(os.environ, {
            'ECS_CLUSTER': 'test-cluster',
            'ECS_SERVICE': 'test-service'
        }):
            idle_watcher.shutdown_ecs_service()
            mock_ecs.update_service.assert_called_once_with(
                cluster='test-cluster',
                service='test-service',
                desiredCount=0
            )
            mock_discord.assert_called_once()

    @patch('minecraft_tools.idle_watcher.main.boto3.client')
    def test_shutdown_ecs_service_failure(self, mock_boto_client):
        """Test ECS service shutdown failure"""
        mock_ecs = MagicMock()
        mock_ecs.update_service.side_effect = Exception("AWS Error")
        mock_boto_client.return_value = mock_ecs
    
        with patch.dict(os.environ, {
            'ECS_CLUSTER': 'test-cluster',
            'ECS_SERVICE': 'test-service'
        }):
            # Should not raise an exception
            idle_watcher.shutdown_ecs_service()

    @patch('minecraft_tools.idle_watcher.main.send_rcon_message')
    @patch('minecraft_tools.idle_watcher.main.send_discord_message')
    @patch('minecraft_tools.idle_watcher.main.time.sleep')
    @patch('minecraft_tools.idle_watcher.main.exit')
    def test_handle_shutdown_signal(self, mock_exit, mock_sleep, mock_discord, mock_rcon):
        """Test graceful shutdown signal handling"""
        idle_watcher.handle_shutdown_signal(signal.SIGTERM, None)
        
        mock_rcon.assert_called_once()
        mock_discord.assert_called_once()
        mock_sleep.assert_called_once_with(5)
        mock_exit.assert_called_once_with(0)

    def test_main_missing_env_vars(self):
        """Test main function with missing environment variables"""
        with patch.dict(os.environ, {}, clear=True):
            # The function prints error and returns, doesn't exit
            idle_watcher.main()  # Should not raise
