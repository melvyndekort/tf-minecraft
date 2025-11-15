"""Tests for Discord bot."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from minecraft_tools.discord_bot.main import create_bot, get_service_status, update_service
from minecraft_tools.config import DiscordBotConfig


class TestDiscordBot:
    """Test Discord bot functionality."""

    def test_create_bot(self):
        """Test bot creation."""
        config = DiscordBotConfig(
            token="test_token",
            ecs_cluster="test_cluster",
            ecs_service="test_service",
            aws_role_arn=None,
            aws_region="us-east-1"
        )
        with patch('minecraft_tools.discord_bot.main.boto3.client') as mock_boto3:
            mock_boto3.return_value = MagicMock()
            bot = create_bot(config)
            assert bot is not None
            assert hasattr(bot, 'tree')

    @pytest.mark.asyncio
    async def test_get_service_status_running(self):
        """Test getting service status when running."""
        mock_ecs = MagicMock()
        mock_ecs.describe_services.return_value = {
            'services': [{
                'desiredCount': 1,
                'runningCount': 1,
                'status': 'ACTIVE'
            }]
        }
        mock_ec2 = MagicMock()
        
        status = await get_service_status(mock_ecs, mock_ec2, "test-cluster", "test-service")
        
        assert status["desired"] == 1
        assert status["running"] == 1

    @pytest.mark.asyncio
    async def test_get_service_status_stopped(self):
        """Test getting service status when stopped."""
        mock_ecs = MagicMock()
        mock_ecs.describe_services.return_value = {
            'services': [{
                'desiredCount': 0,
                'runningCount': 0,
                'status': 'ACTIVE'
            }]
        }
        mock_ec2 = MagicMock()
        
        status = await get_service_status(mock_ecs, mock_ec2, "test-cluster", "test-service")
        
        assert status["desired"] == 0
        assert status["running"] == 0

    @pytest.mark.asyncio
    async def test_update_service_start(self):
        """Test starting service."""
        mock_interaction = AsyncMock()
        mock_interaction.response.send_message = AsyncMock()
        mock_interaction.user.name = "testuser"
        mock_interaction.user.discriminator = "1234"
        
        mock_ecs = MagicMock()
        
        # Mock the get_service_status call and boto3.client call
        with patch('minecraft_tools.discord_bot.main.get_service_status') as mock_get_status, \
             patch('minecraft_tools.discord_bot.main.boto3.client') as mock_boto3:
            mock_get_status.return_value = {"desired": 0, "running": 0}
            mock_boto3.return_value = MagicMock()  # Mock EC2 client
            
            await update_service(mock_interaction, mock_ecs, "test-cluster", "test-service", 1)
            
            mock_ecs.update_service.assert_called_once_with(
                cluster="test-cluster",
                service="test-service",
                desiredCount=1,
                forceNewDeployment=True
            )

    @pytest.mark.asyncio
    async def test_update_service_failure(self):
        """Test service update failure."""
        mock_interaction = AsyncMock()
        mock_interaction.followup.send = AsyncMock()
        mock_interaction.user.name = "testuser"
        mock_interaction.user.discriminator = "1234"
        
        mock_ecs = MagicMock()
        
        # Mock the get_service_status call that happens inside update_service
        with patch('minecraft_tools.discord_bot.main.get_service_status') as mock_get_status:
            mock_get_status.side_effect = Exception("AWS Error")
            
            # Should not raise an exception - error is handled gracefully
            await update_service(mock_interaction, mock_ecs, "test-cluster", "test-service", 1)
