import pytest
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock

# Set test environment variables
os.environ["DISCORD_TOKEN"] = "test_token"
os.environ["ECS_CLUSTER"] = "test_cluster"
os.environ["ECS_SERVICE"] = "test_service"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock everything before importing
with patch('boto3.client'), patch('discord.ext.commands.Bot'):
    from bot import get_service_status, update_service

@pytest.mark.asyncio
async def test_get_service_status():
    mock_ecs = MagicMock()
    mock_ecs.describe_services.return_value = {
        "services": [{
            "desiredCount": 2,
            "runningCount": 1
        }]
    }
    
    with patch("bot.ecs", mock_ecs):
        status = await get_service_status()
        assert status["desired"] == 2
        assert status["running"] == 1

@pytest.mark.asyncio
async def test_update_service_no_change():
    mock_interaction = AsyncMock()
    
    async def mock_get_status():
        return {"desired": 1, "running": 1}
    
    with patch("bot.get_service_status", side_effect=mock_get_status):
        await update_service(mock_interaction, 1)
        mock_interaction.response.send_message.assert_called_once()
        assert "already at desired count" in mock_interaction.response.send_message.call_args[0][0]

@pytest.mark.asyncio
async def test_update_service_success():
    mock_interaction = AsyncMock()
    mock_ecs = MagicMock()
    
    async def mock_get_status():
        return {"desired": 0, "running": 0}
    
    with patch("bot.get_service_status", side_effect=mock_get_status), \
         patch("bot.ecs", mock_ecs):
        await update_service(mock_interaction, 1)
        mock_ecs.update_service.assert_called_once_with(
            cluster="test_cluster",
            service="test_service",
            desiredCount=1
        )
        mock_interaction.response.send_message.assert_called_once()
        assert "updated to desired count = 1" in mock_interaction.response.send_message.call_args[0][0]

@pytest.mark.asyncio
async def test_update_service_error():
    mock_interaction = AsyncMock()
    mock_ecs = MagicMock()
    mock_ecs.update_service.side_effect = Exception("AWS Error")
    
    async def mock_get_status():
        return {"desired": 0, "running": 0}
    
    with patch("bot.get_service_status", side_effect=mock_get_status), \
         patch("bot.ecs", mock_ecs):
        await update_service(mock_interaction, 1)
        mock_interaction.response.send_message.assert_called_once()
        assert "Error updating service" in mock_interaction.response.send_message.call_args[0][0]