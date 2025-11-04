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

# Setup AWS config if role ARN is provided
aws_role_arn = os.getenv("AWS_ROLE_ARN")
aws_region = os.getenv("AWS_DEFAULT_REGION")

if aws_role_arn:
    aws_config_dir = os.path.expanduser("~/.aws")
    os.makedirs(aws_config_dir, exist_ok=True)
    
    config_content = f"""[profile botrole]
role_arn = {aws_role_arn}
source_profile = default
"""
    
    if aws_region:
        config_content += f"region = {aws_region}\n"
    
    with open(os.path.join(aws_config_dir, "config"), "w") as f:
        f.write(config_content)
    
    # Set AWS_PROFILE environment variable
    os.environ["AWS_PROFILE"] = "botrole"

# Initialize AWS clients (will auto-detect region or use AWS_DEFAULT_REGION)
ecs = boto3.client("ecs")
ec2 = boto3.client("ec2")

async def get_service_status() -> dict:
    """Return ECS service info: desired & running counts, and public IPs."""
    logger.info(f"Getting status for service {SERVICE}")
    response = ecs.describe_services(
        cluster=CLUSTER,
        services=[SERVICE]
    )
    service = response["services"][0]
    status = {
        "desired": service["desiredCount"],
        "running": service["runningCount"],
        "public_ips": [],
        "ipv6_ips": []
    }
    
    # Get public IPs if tasks are running
    if status["running"] > 0:
        try:
            tasks_response = ecs.list_tasks(cluster=CLUSTER, serviceName=SERVICE)
            if tasks_response["taskArns"]:
                task_details = ecs.describe_tasks(
                    cluster=CLUSTER,
                    tasks=tasks_response["taskArns"]
                )
                
                for task in task_details["tasks"]:
                    if task["lastStatus"] == "RUNNING":
                        for attachment in task.get("attachments", []):
                            if attachment["type"] == "ElasticNetworkInterface":
                                for detail in attachment["details"]:
                                    if detail["name"] == "networkInterfaceId":
                                        eni_id = detail["value"]
                                        eni_response = ec2.describe_network_interfaces(
                                            NetworkInterfaceIds=[eni_id]
                                        )
                                        eni = eni_response["NetworkInterfaces"][0]
                                        
                                        # Get IPv4 public IP
                                        public_ip = eni.get("Association", {}).get("PublicIp")
                                        if public_ip:
                                            status["public_ips"].append(public_ip)
                                        
                                        # Get IPv6 addresses
                                        for ipv6 in eni.get("Ipv6Addresses", []):
                                            status["ipv6_ips"].append(ipv6["Ipv6Address"])
        except Exception as e:
            logger.warning(f"Failed to get public IPs: {e}")
    
    logger.info(f"Service status: desired={status['desired']}, running={status['running']}, public_ips={status['public_ips']}, ipv6_ips={status['ipv6_ips']}")
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
            message = f"ℹ️ Service `{SERVICE}`: desired = {status['desired']}, running = {status['running']}"
            
            if status['public_ips']:
                ips = ", ".join(status['public_ips'])
                message += f"\n🌐 IPv4: {ips}"
            
            if status['ipv6_ips']:
                ipv6s = ", ".join(status['ipv6_ips'])
                message += f"\n🌐 IPv6: {ipv6s}"
            
            await interaction.response.send_message(message)
        except Exception as e:
            logger.error(f"Error fetching status: {e}")
            await interaction.response.send_message(f"❌ Error fetching status: {e}")
    
    @bot.tree.command(name="help", description="Show all available commands")
    async def help_command(interaction: discord.Interaction):
        logger.info(f"Help command invoked by {interaction.user.name}")
        help_text = (
            "🎮 **Minecraft Server Commands**\n\n"
            "`/server-start` - Start the Minecraft server\n"
            "`/server-stop` - Stop the Minecraft server\n"
            "`/server-status` - Check current server status\n"
            "`/help` - Show this help message"
        )
        await interaction.response.send_message(help_text)
    
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

def main():
    logger.info("Creating and starting Discord bot")
    bot = create_bot()
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    main()
