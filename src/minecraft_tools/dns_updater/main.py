"""DNS updater for Minecraft server IP addresses."""

import logging
import time
from typing import Any

import boto3
import requests
from botocore.exceptions import ClientError

from minecraft_tools.config import DNSUpdaterConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class CloudflareAPI:
    """Cloudflare API client."""

    def __init__(self, token: str) -> None:
        self.token = token
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def get_dns_record(
        self, zone_id: str, record_name: str
    ) -> dict[str, Any] | None:
        """Get DNS record by name."""
        try:
            response = requests.get(
                f"{self.base_url}/zones/{zone_id}/dns_records",
                headers=self.headers,
                params={"name": record_name, "type": "A"},
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            if data["success"] and data["result"]:
                return data["result"][0]
            return None
        except requests.RequestException as e:
            logger.error(f"Failed to get DNS record: {e}")
            raise

    def update_dns_record(
        self, zone_id: str, record_id: str, record_name: str, ip_address: str
    ) -> bool:
        """Update DNS record with new IP address."""
        try:
            response = requests.put(
                f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}",
                headers=self.headers,
                json={
                    "type": "A",
                    "name": record_name,
                    "content": ip_address,
                    "ttl": 300,
                },
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            return data["success"]
        except requests.RequestException as e:
            logger.error(f"Failed to update DNS record: {e}")
            raise


def get_service_public_ips(
    ecs_client: Any, ec2_client: Any, cluster: str, service: str
) -> list[str]:
    """Get public IP addresses for ECS service tasks."""
    try:
        # Get running tasks
        tasks_response = ecs_client.list_tasks(cluster=cluster, serviceName=service)
        if not tasks_response["taskArns"]:
            logger.info("No running tasks found")
            return []

        # Get task details
        task_details = ecs_client.describe_tasks(
            cluster=cluster, tasks=tasks_response["taskArns"]
        )

        ips = []
        for task in task_details["tasks"]:
            for attachment in task.get("attachments", []):
                if attachment["type"] == "ElasticNetworkInterface":
                    for detail in attachment["details"]:
                        if detail["name"] == "networkInterfaceId":
                            eni_id = detail["value"]
                            try:
                                eni_response = ec2_client.describe_network_interfaces(
                                    NetworkInterfaceIds=[eni_id]
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

        return ips
    except ClientError as e:
        logger.error(f"AWS error getting service IPs: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting service IPs: {e}")
        raise


def update_dns_if_needed(config: DNSUpdaterConfig) -> None:
    """Update DNS record if IP address has changed."""
    try:
        # Initialize clients
        ecs_client = boto3.client("ecs")
        ec2_client = boto3.client("ec2")
        cloudflare = CloudflareAPI(config.cloudflare_token)

        # Get current service IPs
        current_ips = get_service_public_ips(
            ecs_client, ec2_client, config.ecs_cluster, config.ecs_service
        )

        if not current_ips:
            logger.info("No public IPs found for service, skipping DNS update")
            return

        # Use first IP (assuming single task)
        current_ip = current_ips[0]
        logger.info(f"Current service IP: {current_ip}")

        # Get current DNS record
        dns_record = cloudflare.get_dns_record(config.zone_id, config.record_name)
        if not dns_record:
            logger.error(f"DNS record {config.record_name} not found")
            return

        current_dns_ip = dns_record["content"]
        logger.info(f"Current DNS IP: {current_dns_ip}")

        # Update if different
        if current_ip != current_dns_ip:
            logger.info(f"Updating DNS record from {current_dns_ip} to {current_ip}")
            success = cloudflare.update_dns_record(
                config.zone_id, dns_record["id"], config.record_name, current_ip
            )
            if success:
                logger.info("DNS record updated successfully")
            else:
                logger.error("Failed to update DNS record")
        else:
            logger.info("DNS record is already up to date")

    except Exception as e:
        logger.error(f"Error updating DNS: {e}")
        raise


def main() -> None:
    """Main entry point."""
    try:
        config = DNSUpdaterConfig.from_env()
        logger.info(f"Starting DNS updater for {config.record_name}")

        while True:
            update_dns_if_needed(config)
            logger.info("Sleeping for 60 seconds...")
            time.sleep(60)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except KeyboardInterrupt:
        logger.info("DNS updater stopped by user")
    except Exception as e:
        logger.error(f"DNS updater failed: {e}")
        raise


if __name__ == "__main__":
    main()
