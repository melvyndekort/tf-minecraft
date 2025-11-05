import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Set test environment variables
os.environ["DISCORD_TOKEN"] = "test_token"
os.environ["ECS_CLUSTER"] = "test_cluster"
os.environ["ECS_SERVICE"] = "test_service"

# Mock everything before importing
with patch('boto3.client'), patch('discord.ext.commands.Bot'):
    from minecraft_tools.discord_bot.main import get_service_status, update_service, create_bot


def test_create_bot():
    """Test bot creation and command registration"""
    mock_bot = MagicMock()
    mock_bot.tree = MagicMock()
    
    with patch('discord.ext.commands.Bot', return_value=mock_bot):
        bot = create_bot()
        
        # Check commands were registered
        assert mock_bot.tree.command.call_count == 4  # start, stop, status, help commands
        assert bot == mock_bot


@pytest.mark.asyncio
async def test_get_service_status():
    """Test service status retrieval with IP addresses"""
    mock_ecs = MagicMock()
    mock_ec2 = MagicMock()
    
    mock_ecs.describe_services.return_value = {
        "services": [{"desiredCount": 1, "runningCount": 1}]
    }
    mock_ecs.list_tasks.return_value = {"taskArns": ["task-arn"]}
    mock_ecs.describe_tasks.return_value = {
        "tasks": [{
            "lastStatus": "RUNNING",
            "attachments": [{
                "type": "ElasticNetworkInterface",
                "details": [{"name": "networkInterfaceId", "value": "eni-123"}]
            }]
        }]
    }
    mock_ec2.describe_network_interfaces.return_value = {
        "NetworkInterfaces": [{
            "Association": {"PublicIp": "1.2.3.4"},
            "Ipv6Addresses": [{"Ipv6Address": "2001:db8::1"}]
        }]
    }
    
    with patch("minecraft_tools.discord_bot.main.ecs", mock_ecs), \
         patch("minecraft_tools.discord_bot.main.ec2", mock_ec2):
        status = await get_service_status()
        assert status["desired"] == 1
        assert status["running"] == 1
        assert status["public_ips"] == ["1.2.3.4"]
        assert status["ipv6_ips"] == ["2001:db8::1"]


@pytest.mark.asyncio
async def test_get_service_status_no_tasks():
    """Test service status when no tasks are running"""
    mock_ecs = MagicMock()
    mock_ecs.describe_services.return_value = {
        "services": [{"desiredCount": 0, "runningCount": 0}]
    }
    
    with patch("minecraft_tools.discord_bot.main.ecs", mock_ecs):
        status = await get_service_status()
        assert status["desired"] == 0
        assert status["running"] == 0
        assert status["public_ips"] == []


@pytest.mark.asyncio
async def test_get_service_status_no_eni():
    """Test service status when task has no ENI"""
    mock_ecs = MagicMock()
    mock_ec2 = MagicMock()
    
    mock_ecs.describe_services.return_value = {
        "services": [{"desiredCount": 1, "runningCount": 1}]
    }
    mock_ecs.list_tasks.return_value = {"taskArns": ["task-arn"]}
    mock_ecs.describe_tasks.return_value = {
        "tasks": [{
            "lastStatus": "RUNNING",
            "attachments": []  # No ENI attachment
        }]
    }
    
    with patch("minecraft_tools.discord_bot.main.ecs", mock_ecs), \
         patch("minecraft_tools.discord_bot.main.ec2", mock_ec2):
        status = await get_service_status()
        assert status["desired"] == 1
        assert status["running"] == 1
        assert status["public_ips"] == []
        assert status["ipv6_ips"] == []



@pytest.mark.asyncio
async def test_update_service_no_change_needed():
    """Test update when service is already at desired count"""
    mock_interaction = AsyncMock()
    
    with patch("minecraft_tools.discord_bot.main.get_service_status", 
               return_value={"desired": 1, "running": 1}):
        await update_service(mock_interaction, 1)
        mock_interaction.response.send_message.assert_called_once()
        assert "already at desired count" in mock_interaction.response.send_message.call_args[0][0]


@pytest.mark.asyncio
async def test_update_service_success():
    """Test successful service update"""
    mock_interaction = AsyncMock()
    mock_ecs = MagicMock()
    
    with patch("minecraft_tools.discord_bot.main.get_service_status", 
               return_value={"desired": 0, "running": 0}), \
         patch("minecraft_tools.discord_bot.main.ecs", mock_ecs):
        await update_service(mock_interaction, 1)
        mock_ecs.update_service.assert_called_once_with(
            cluster="test_cluster", service="test_service", desiredCount=1
        )


@pytest.mark.asyncio
async def test_update_service_aws_error():
    """Test service update with AWS error"""
    mock_interaction = AsyncMock()
    mock_ecs = MagicMock()
    mock_ecs.update_service.side_effect = Exception("AWS Error")
    
    with patch("minecraft_tools.discord_bot.main.get_service_status", 
               return_value={"desired": 0, "running": 0}), \
         patch("minecraft_tools.discord_bot.main.ecs", mock_ecs):
        await update_service(mock_interaction, 1)
        mock_interaction.response.send_message.assert_called_once()
        assert "Error updating service" in mock_interaction.response.send_message.call_args[0][0]
