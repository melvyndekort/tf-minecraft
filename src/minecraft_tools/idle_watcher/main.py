"""Idle watcher for Minecraft server - shuts down server when no players are online."""

import logging
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError
from mcrcon import MCRcon

from minecraft_tools.config import IdleWatcherConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_player_count(host: str, port: int, password: str = "") -> int:
    """Get current player count from Minecraft server."""
    try:
        with MCRcon(host, password, port=port) as mcr:
            response = mcr.command("list")
            # Parse response like "There are 0 of a max of 20 players online:"
            if "There are" in response:
                parts = response.split()
                if len(parts) >= 3:
                    return int(parts[2])
        return 0
    except Exception as e:
        logger.warning(f"Failed to get player count: {e}")
        return -1  # Return -1 to indicate error


def get_service_status(ecs_client: Any, cluster: str, service: str) -> dict[str, int]:
    """Get ECS service status."""
    try:
        response = ecs_client.describe_services(cluster=cluster, services=[service])
        if not response["services"]:
            raise ValueError(f"Service {service} not found in cluster {cluster}")

        service_info = response["services"][0]
        return {
            "desired": service_info["desiredCount"],
            "running": service_info["runningCount"],
        }
    except ClientError as e:
        logger.error(f"AWS error getting service status: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting service status: {e}")
        raise


def scale_service(
    ecs_client: Any, cluster: str, service: str, desired_count: int
) -> bool:
    """Scale ECS service to desired count."""
    try:
        ecs_client.update_service(
            cluster=cluster,
            service=service,
            desiredCount=desired_count,
        )
        logger.info(f"Scaled service {service} to {desired_count} tasks")
        return True
    except ClientError as e:
        logger.error(f"AWS error scaling service: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error scaling service: {e}")
        return False


def monitor_server(config: IdleWatcherConfig) -> None:
    """Monitor server and shut down if idle."""
    ecs_client = boto3.client("ecs")
    idle_start_time = None

    while True:
        try:
            # Check service status
            status = get_service_status(
                ecs_client, config.ecs_cluster, config.ecs_service
            )

            if status["running"] == 0:
                logger.info("Service is not running, resetting idle timer")
                idle_start_time = None
                time.sleep(config.check_interval)
                continue

            # Get player count
            player_count = get_player_count(
                config.minecraft_host, config.minecraft_port
            )

            if player_count == -1:
                logger.warning("Could not get player count, assuming server is busy")
                idle_start_time = None
            elif player_count == 0:
                current_time = time.time()

                if idle_start_time is None:
                    idle_start_time = current_time
                    logger.info("Server is idle, starting idle timer")
                else:
                    idle_duration = current_time - idle_start_time
                    logger.info(f"Server idle for {idle_duration:.0f} seconds")

                    if idle_duration >= config.idle_threshold:
                        logger.info("Server has been idle too long, shutting down")
                        if scale_service(
                            ecs_client, config.ecs_cluster, config.ecs_service, 0
                        ):
                            logger.info("Server shutdown initiated")
                            idle_start_time = None
                        else:
                            logger.error("Failed to shut down server")
            else:
                logger.info(f"Server has {player_count} players, resetting idle timer")
                idle_start_time = None

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            idle_start_time = None  # Reset on error to be safe

        time.sleep(config.check_interval)


def main() -> None:
    """Main entry point."""
    try:
        config = IdleWatcherConfig.from_env()
        logger.info(
            f"Starting idle watcher for {config.minecraft_host}:{config.minecraft_port} "
            f"(check every {config.check_interval}s, idle threshold {config.idle_threshold}s)"
        )

        monitor_server(config)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except KeyboardInterrupt:
        logger.info("Idle watcher stopped by user")
    except Exception as e:
        logger.error(f"Idle watcher failed: {e}")
        raise


if __name__ == "__main__":
    main()
