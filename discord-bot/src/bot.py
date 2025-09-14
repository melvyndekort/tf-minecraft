import os
import logging
import discord
import boto3
from discord import app_commands
from discord.ext import commands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress Discord.py warnings we don't care about
logging.getLogger('discord.ext.commands.bot').setLevel(logging.ERROR)
logging.getLogger('discord.client').setLevel(logging.WARNING)

TOKEN = os.getenv("DISCORD_TOKEN")
CLUSTER = os.getenv("ECS_CLUSTER")
SERVICE = os.getenv("ECS_SERVICE")

logger.info(f"Starting Discord bot for ECS cluster: {CLUSTER}, service: {SERVICE}")

ecs = boto3.client("ecs")

async def get_service_status() -> dict:
    """Return ECS service info: desired & running counts."""
    logger.info(f"Getting status for service {SERVICE}")
    response = ecs.describe_services(
        cluster=CLUSTER,
        services=[SERVICE]
    )
    service = response["services"][0]
    status = {
        "desired": service["desiredCount"],
        "running": service["runningCount"]
    }
    logger.info(f"Service status: desired={status['desired']}, running={status['running']}")
    return status

async def update_service(interaction: discord.Interaction, desired_count: int):
    """Scale ECS service only if needed."""
    user = f"{interaction.user.name}#{interaction.user.discriminator}"
    logger.info(f"User {user} requested service scale to {desired_count}")
    
    status = await get_service_status()
    current_desired = status["desired"]
    
    if current_desired == desired_count:
        logger.info(f"Service already at desired count {desired_count}, no action needed")
        await interaction.response.send_message(
            f"ℹ️ Service `{SERVICE}` is already at desired count = {desired_count} (running = {status['running']})"
        )
        return

    try:
        logger.info(f"Scaling service from {current_desired} to {desired_count}")
        ecs.update_service(
            cluster=CLUSTER,
            service=SERVICE,
            desiredCount=desired_count
        )
        logger.info(f"Successfully updated service to desired count {desired_count}")
        await interaction.response.send_message(
            f"✅ Service `{SERVICE}` updated to desired count = {desired_count}"
        )
    except Exception as e:
        logger.error(f"Failed to update service: {e}")
        await interaction.response.send_message(f"❌ Error updating service: {e}")

def create_bot():
    """Create and configure the Discord bot."""
    intents = discord.Intents.default()
    intents.message_content = False  # Disable privileged intent - not needed for slash commands
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    @bot.tree.command(name="server-start", description="Scale ECS service to 1 task")
    async def server_start(interaction: discord.Interaction):
        logger.info(f"Server start command invoked by {interaction.user.name}")
        await update_service(interaction, 1)
    
    @bot.tree.command(name="server-stop", description="Scale ECS service to 0 tasks")
    async def server_stop(interaction: discord.Interaction):
        logger.info(f"Server stop command invoked by {interaction.user.name}")
        await update_service(interaction, 0)
    
    @bot.tree.command(name="server-status", description="Check ECS service status")
    async def server_status(interaction: discord.Interaction):
        logger.info(f"Server status command invoked by {interaction.user.name}")
        try:
            status = await get_service_status()
            await interaction.response.send_message(
                f"ℹ️ Service `{SERVICE}`: desired = {status['desired']}, running = {status['running']}"
            )
        except Exception as e:
            logger.error(f"Error fetching status: {e}")
            await interaction.response.send_message(f"❌ Error fetching status: {e}")
    
    @bot.event
    async def on_ready():
        logger.info(f"Bot logged in as {bot.user}")
        await bot.tree.sync()
        logger.info("Command tree synced successfully")
    
    @bot.event
    async def on_command_error(ctx, error):
        logger.error(f"Command error: {error}")
    
    @bot.event
    async def on_error(event, *args, **kwargs):
        logger.error(f"Bot error in {event}: {args}")
    
    return bot

if __name__ == "__main__":
    logger.info("Creating and starting Discord bot")
    bot = create_bot()
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise
