import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import idle_watcher


class TestIdleWatcher:
    
    @patch('idle_watcher.requests.post')
    def test_send_discord_message_success(self, mock_post):
        """Test successful Discord message sending"""
        with patch.dict(os.environ, {'DISCORD_WEBHOOK': 'http://test.webhook'}):
            idle_watcher.send_discord_message("Test message")
            mock_post.assert_called_once_with(
                'http://test.webhook', 
                json={"content": "Test message"}
            )
    
    def test_send_discord_message_no_webhook(self):
        """Test Discord message when no webhook is configured"""
        with patch.dict(os.environ, {}, clear=True):
            # Should not raise an exception
            idle_watcher.send_discord_message("Test message")
    
    @patch('idle_watcher.send_discord_message')
    @patch('idle_watcher.MCRcon')
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
        assert idle_watcher.server_available == True
        mock_discord.assert_called_once_with("🟢 Minecraft server is online and reachable at `mc.example.com`")
    
    @patch('idle_watcher.send_discord_message')
    @patch('idle_watcher.MCRcon')
    def test_get_player_count_server_already_available(self, mock_mcrcon, mock_discord):
        """Test no Discord notification when server is already available"""
        mock_mcr = MagicMock()
        mock_mcr.command.return_value = "There are 1 of a max of 20 players online: Player1"
        mock_mcrcon.return_value.__enter__.return_value = mock_mcr
        
        # Set server as already available
        idle_watcher.server_available = True
        
        count = idle_watcher.get_player_count()
        
        assert count == 1
        mock_discord.assert_not_called()
    
    @patch('idle_watcher.MCRcon')
    def test_get_player_count_no_players(self, mock_mcrcon):
        """Test getting player count when no players are online"""
        mock_mcr = MagicMock()
        mock_mcr.command.return_value = "There are 0 of a max of 20 players online:"
        mock_mcrcon.return_value.__enter__.return_value = mock_mcr
        
        # Set server as already available to avoid Discord notification
        idle_watcher.server_available = True
        
        count = idle_watcher.get_player_count()
        assert count == 0
    
    @patch('idle_watcher.MCRcon')
    def test_get_player_count_connection_error(self, mock_mcrcon):
        """Test getting player count when connection fails"""
        mock_mcrcon.side_effect = Exception("Connection failed")
        
        count = idle_watcher.get_player_count()
        assert count == 0
        assert idle_watcher.server_available == False
    
    @patch('idle_watcher.boto3.client')
    @patch('idle_watcher.send_discord_message')
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
    
    @patch('idle_watcher.boto3.client')
    def test_shutdown_ecs_service_failure(self, mock_boto_client):
        """Test ECS service shutdown failure"""
        mock_ecs = MagicMock()
        mock_ecs.update_service.side_effect = Exception("AWS Error")
        mock_boto_client.return_value = mock_ecs
        
        # Should not raise an exception
        idle_watcher.shutdown_ecs_service()
