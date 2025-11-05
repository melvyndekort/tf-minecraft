"""Tests for DNS updater."""

from unittest.mock import MagicMock

import responses

from minecraft_tools.dns_updater.main import CloudflareAPI, get_service_public_ips


class TestCloudflareAPI:
    """Test Cloudflare API client."""

    @responses.activate
    def test_get_dns_record_success(self):
        """Test successful DNS record retrieval."""
        responses.add(
            responses.GET,
            "https://api.cloudflare.com/client/v4/zones/test-zone/dns_records",
            json={
                "success": True,
                "result": [
                    {
                        "id": "record-123",
                        "name": "test.example.com",
                        "content": "1.2.3.4",
                        "type": "A",
                    }
                ],
            },
        )

        client = CloudflareAPI("test-token")
        record = client.get_dns_record("test-zone", "test.example.com")

        assert record is not None
        assert record["id"] == "record-123"
        assert record["content"] == "1.2.3.4"

    @responses.activate
    def test_get_dns_record_not_found(self):
        """Test DNS record not found."""
        responses.add(
            responses.GET,
            "https://api.cloudflare.com/client/v4/zones/test-zone/dns_records",
            json={"success": True, "result": []},
        )

        client = CloudflareAPI("test-token")
        record = client.get_dns_record("test-zone", "test.example.com")

        assert record is None

    @responses.activate
    def test_update_dns_record_success(self):
        """Test successful DNS record update."""
        responses.add(
            responses.PUT,
            "https://api.cloudflare.com/client/v4/zones/test-zone/dns_records/record-123",
            json={"success": True},
        )

        client = CloudflareAPI("test-token")
        result = client.update_dns_record(
            "test-zone", "record-123", "test.example.com", "5.6.7.8"
        )

        assert result is True

    @responses.activate
    def test_update_dns_record_failure(self):
        """Test DNS record update failure."""
        responses.add(
            responses.PUT,
            "https://api.cloudflare.com/client/v4/zones/test-zone/dns_records/record-123",
            json={"success": False, "errors": ["Update failed"]},
        )

        client = CloudflareAPI("test-token")
        result = client.update_dns_record(
            "test-zone", "record-123", "test.example.com", "5.6.7.8"
        )

        assert result is False


class TestGetServicePublicIPs:
    """Test getting service public IPs."""

    def test_get_service_public_ips_success(self):
        """Test successful retrieval of public IPs."""
        # Mock ECS client
        mock_ecs = MagicMock()
        mock_ecs.describe_services.return_value = {
            "services": [{"taskDefinition": "test-task-def"}]
        }
        mock_ecs.list_tasks.return_value = {
            "taskArns": ["arn:aws:ecs:region:account:task/cluster/task-id"]
        }
        mock_ecs.describe_tasks.return_value = {
            "tasks": [
                {
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {"name": "networkInterfaceId", "value": "eni-12345"}
                            ],
                        }
                    ]
                }
            ]
        }

        # Mock EC2 client
        mock_ec2 = MagicMock()
        mock_ec2.describe_network_interfaces.return_value = {
            "NetworkInterfaces": [{"Association": {"PublicIp": "1.2.3.4"}}]
        }

        ips = get_service_public_ips(mock_ecs, mock_ec2, "test-cluster", "test-service")
        assert ips == ["1.2.3.4"]

    def test_get_service_public_ips_no_tasks(self):
        """Test when no tasks are running."""
        mock_ecs = MagicMock()
        mock_ecs.describe_services.return_value = {
            "services": [{"taskDefinition": "test-task-def"}]
        }
        mock_ecs.list_tasks.return_value = {"taskArns": []}

        mock_ec2 = MagicMock()

        ips = get_service_public_ips(mock_ecs, mock_ec2, "test-cluster", "test-service")
        assert ips == []

    def test_get_service_public_ips_no_public_ip(self):
        """Test when tasks have no public IP."""
        mock_ecs = MagicMock()
        mock_ecs.describe_services.return_value = {
            "services": [{"taskDefinition": "test-task-def"}]
        }
        mock_ecs.list_tasks.return_value = {
            "taskArns": ["arn:aws:ecs:region:account:task/cluster/task-id"]
        }
        mock_ecs.describe_tasks.return_value = {
            "tasks": [
                {
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                {"name": "networkInterfaceId", "value": "eni-12345"}
                            ],
                        }
                    ]
                }
            ]
        }

        # Mock EC2 client with no public IP
        mock_ec2 = MagicMock()
        mock_ec2.describe_network_interfaces.return_value = {
            "NetworkInterfaces": [{}]  # No Association key
        }

        ips = get_service_public_ips(mock_ecs, mock_ec2, "test-cluster", "test-service")
        assert ips == []
