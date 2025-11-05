"""Tests for health check module."""

from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from minecraft_tools.health import check_aws_connectivity, check_ecs_service


class TestCheckAWSConnectivity:
    """Test AWS connectivity check."""

    @patch("boto3.client")
    def test_check_aws_connectivity_success(self, mock_boto_client):
        """Test successful AWS connectivity check."""
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            "Account": "123456789012",
            "UserId": "AIDACKCEVSQ6C2EXAMPLE",
        }
        mock_boto_client.return_value = mock_sts

        result = check_aws_connectivity()

        assert result["status"] == "healthy"
        assert result["account"] == "123456789012"
        assert result["user_id"] == "AIDACKCEVSQ6C2EXAMPLE"

    @patch("boto3.client")
    def test_check_aws_connectivity_failure(self, mock_boto_client):
        """Test AWS connectivity check failure."""
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "GetCallerIdentity",
        )
        mock_boto_client.return_value = mock_sts

        result = check_aws_connectivity()

        assert result["status"] == "unhealthy"
        assert "error" in result


class TestCheckECSService:
    """Test ECS service health check."""

    @patch("boto3.client")
    def test_check_ecs_service_success(self, mock_boto_client):
        """Test successful ECS service check."""
        mock_ecs = MagicMock()
        mock_ecs.describe_services.return_value = {
            "services": [{"desiredCount": 1, "runningCount": 1, "status": "ACTIVE"}]
        }
        mock_boto_client.return_value = mock_ecs

        result = check_ecs_service("test-cluster", "test-service")

        assert result["status"] == "healthy"
        assert result["desired"] == 1
        assert result["running"] == 1
        assert result["service_status"] == "ACTIVE"

    @patch("boto3.client")
    def test_check_ecs_service_not_found(self, mock_boto_client):
        """Test ECS service check when service not found."""
        mock_ecs = MagicMock()
        mock_ecs.describe_services.return_value = {"services": []}
        mock_boto_client.return_value = mock_ecs

        result = check_ecs_service("test-cluster", "test-service")

        assert result["status"] == "unhealthy"
        assert "Service test-service not found" in result["error"]

    @patch("boto3.client")
    def test_check_ecs_service_aws_error(self, mock_boto_client):
        """Test ECS service check with AWS error."""
        mock_ecs = MagicMock()
        mock_ecs.describe_services.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ClusterNotFoundException",
                    "Message": "Cluster not found",
                }
            },
            "DescribeServices",
        )
        mock_boto_client.return_value = mock_ecs

        result = check_ecs_service("test-cluster", "test-service")

        assert result["status"] == "unhealthy"
        assert "error" in result
