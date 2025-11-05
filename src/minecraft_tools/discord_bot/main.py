"""Discord bot for managing Minecraft ECS service."""

import logging
import os
from typing import Any

import boto3
import discord
from botocore.exceptions import ClientError
from discord.ext import commands

from minecraft_tools.config import DiscordBotConfig
from minecraft_tools.logging_config import setup_logging

logger = logging.getLogger(__name__)


def setup_aws_profile(config: DiscordBotConfig) -> None:
    """Setup AWS profile for role assumption."""
    if not config.aws_role_arn:
        return

    aws_config_dir = os.path.expanduser("~/.aws")
    os.makedirs(aws_config_dir, exist_ok=True)

    config_content = f"""[profile botrole]
role_arn = {config.aws_role_arn}
source_profile = default
"""

    if config.aws_region:
        config_content += f"region = {config.aws_region}\n"

    with open(os.path.join(aws_config_dir, "config"), "w") as f:
        f.write(config_content)

    # Set AWS_PROFILE environment variable
    os.environ["AWS_PROFILE"] = "botrole"


async def get_service_status(
    ecs_client: Any, ec2_client: Any, cluster: str, service: str
) -> dict[str, Any]:
    """Get ECS service status with IP addresses."""
    try:
        response = ecs_client.describe_services(cluster=cluster, services=[service])
        if not response["services"]:
            raise ValueError(f"Service {service} not found in cluster {cluster}")

        service_info = response["services"][0]
        desired = service_info["desiredCount"]
        running = service_info["runningCount"]

        # Get task IPs if tasks are running
        ips = []
        if running > 0:
            tasks_response = ecs_client.list_tasks(cluster=cluster, serviceName=service)
            if tasks_response["taskArns"]:
                task_details = ecs_client.describe_tasks(
                    cluster=cluster, tasks=tasks_response["taskArns"]
                )

                for task in task_details["tasks"]:
                    for attachment in task.get("attachments", []):
                        if attachment["type"] == "ElasticNetworkInterface":
                            for detail in attachment["details"]:
                                if detail["name"] == "networkInterfaceId":
                                    eni_id = detail["value"]
                                    try:
                                        eni_response = (
                                            ec2_client.describe_network_interfaces(
                                                NetworkInterfaceIds=[eni_id]
                                            )
                                        )
                                        if eni_response["NetworkInterfaces"]:
                                            public_ip = (
                                                eni_response["NetworkInterfaces"][0]
                                                .get("Association", {})
                                                .get("PublicIp")
                                            )
                                            if public_ip:
                                                ips.append(public_ip)
                                    except ClientError as e:
                                        logger.warning(
                                            f"Failed to get IP for ENI {eni_id}: {e}"
                                        )

        return {
            "desired": desired,
            "running": running,
            "ips": ips,
        }
    except ClientError as e:
        logger.error(f"AWS error getting service status: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting service status: {e}")
        raise


async def update_service(
    interaction: discord.Interaction,
    ecs_client: Any,
    cluster: str,
    service: str,
    desired_count: int,
) -> None:
    """Scale ECS service only if needed."""
    user = f"{interaction.user.name}#{interaction.user.discriminator}"
    logger.info(f"User {user} requested service scale to {desired_count}")

    try:
        # Get current status
        ec2_client = boto3.client("ec2")
        status = await get_service_status(ecs_client, ec2_client, cluster, service)
        current_desired = status["desired"]

        if current_desired == desired_count:
            logger.info(
                f"Service already at desired count {desired_count}, no action needed"
            )
            await interaction.response.send_message(
                f"ℹ️ Service `{service}` is already at desired count = {desired_count} "
                f"(running = {status['running']})"
            )
            return

        logger.info(f"Scaling service from {current_desired} to {desired_count}")
        ecs_client.update_service(
            cluster=cluster,
            service=service,
            desiredCount=desired_count,
        )
        logger.info(f"Successfully updated service to desired count {desired_count}")
        await interaction.response.send_message(
            f"✅ Service `{service}` updated to desired count = {desired_count}"
        )
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(f"AWS error updating service: {error_code} - {e}")
        await interaction.response.send_message(f"❌ AWS error: {error_code}")
    except Exception as e:
        logger.error(f"Unexpected error updating service: {e}")
        await interaction.response.send_message(f"❌ Error updating service: {e}")


def create_bot(config: DiscordBotConfig) -> commands.Bot:
    """Create and configure the Discord bot."""
    intents = discord.Intents.default()
    intents.message_content = (
        False  # Disable privileged intent - not needed for slash commands
    )
    bot = commands.Bot(command_prefix="!", intents=intents)

    # Initialize AWS clients
    ecs_client = boto3.client("ecs")
    ec2_client = boto3.client("ec2")

    @bot.tree.command(name="server-start", description="Scale ECS service to 1 task")
    async def server_start(interaction: discord.Interaction) -> None:
        logger.info(f"Server start command invoked by {interaction.user.name}")
        await update_service(
            interaction, ecs_client, config.ecs_cluster, config.ecs_service, 1
        )

    @bot.tree.command(name="server-stop", description="Scale ECS service to 0 tasks")
    async def server_stop(interaction: discord.Interaction) -> None:
        logger.info(f"Server stop command invoked by {interaction.user.name}")
        await update_service(
            interaction, ecs_client, config.ecs_cluster, config.ecs_service, 0
        )

    @bot.tree.command(name="server-status", description="Check ECS service status")
    async def server_status(interaction: discord.Interaction) -> None:
        logger.info(f"Server status command invoked by {interaction.user.name}")
        try:
            status = await get_service_status(
                ecs_client, ec2_client, config.ecs_cluster, config.ecs_service
            )

            message = (
                f"📊 **Service Status**\n"
                f"Service: `{config.ecs_service}`\n"
                f"Desired: {status['desired']}\n"
                f"Running: {status['running']}"
            )

            if status["ips"]:
                ips_str = ", ".join(status["ips"])
                message += f"\nPublic IPs: {ips_str}"

            await interaction.response.send_message(message)
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            await interaction.response.send_message(f"❌ Error getting status: {e}")

    @bot.tree.command(name="help", description="Show available commands")
    async def help_command(interaction: discord.Interaction) -> None:
        help_text = """
🎮 **Minecraft Server Bot Commands**

`/server-start` - Start the Minecraft server (scale to 1 task)
`/server-stop` - Stop the Minecraft server (scale to 0 tasks)
`/server-status` - Check current server status and IP addresses
`/help` - Show this help message

The server runs on AWS ECS Fargate and may take a few minutes to start up.
        """
        await interaction.response.send_message(help_text)

    @bot.event
    async def on_ready() -> None:
        logger.info(f"Bot logged in as {bot.user}")
        try:
            synced = await bot.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    return bot


def main() -> None:
    """Main entry point."""
    try:
        # Setup logging
        structured = os.getenv("STRUCTURED_LOGGING", "false").lower() == "true"
        log_level = os.getenv("LOG_LEVEL", "INFO")
        setup_logging(log_level, structured)

        config = DiscordBotConfig.from_env()
        logger.info(
            f"Starting Discord bot for ECS cluster: {config.ecs_cluster}, service: {config.ecs_service}"
        )

        setup_aws_profile(config)
        bot = create_bot(config)
        bot.run(config.token)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    main()
