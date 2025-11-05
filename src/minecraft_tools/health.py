"""Health check utilities."""

import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def check_aws_connectivity() -> dict[str, Any]:
    """Check AWS connectivity and permissions."""
    try:
        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        return {
            "status": "healthy",
            "account": identity.get("Account"),
            "user_id": identity.get("UserId"),
        }
    except ClientError as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


def check_ecs_service(cluster: str, service: str) -> dict[str, Any]:
    """Check ECS service health."""
    try:
        ecs = boto3.client("ecs")
        response = ecs.describe_services(cluster=cluster, services=[service])

        if not response["services"]:
            return {
                "status": "unhealthy",
                "error": f"Service {service} not found",
            }

        service_info = response["services"][0]
        return {
            "status": "healthy",
            "desired": service_info["desiredCount"],
            "running": service_info["runningCount"],
            "service_status": service_info["status"],
        }
    except ClientError as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
