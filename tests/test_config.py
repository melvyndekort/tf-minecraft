"""Tests for configuration module."""

import os
from unittest.mock import patch

import pytest

from minecraft_tools.config import DiscordBotConfig, DNSUpdaterConfig, IdleWatcherConfig


class TestDiscordBotConfig:
    """Test Discord bot configuration."""

    def test_from_env_complete(self):
        """Test configuration with all environment variables."""
        env_vars = {
            "DISCORD_TOKEN": "test_token",
            "ECS_CLUSTER": "test_cluster",
            "ECS_SERVICE": "test_service",
            "AWS_ROLE_ARN": "arn:aws:iam::123:role/test",
            "AWS_DEFAULT_REGION": "us-east-1",
        }

        with patch.dict(os.environ, env_vars):
            config = DiscordBotConfig.from_env()

        assert config.token == "test_token"
        assert config.ecs_cluster == "test_cluster"
        assert config.ecs_service == "test_service"
        assert config.aws_role_arn == "arn:aws:iam::123:role/test"
        assert config.aws_region == "us-east-1"

    def test_from_env_minimal(self):
        """Test configuration with only required variables."""
        env_vars = {
            "DISCORD_TOKEN": "test_token",
            "ECS_CLUSTER": "test_cluster",
            "ECS_SERVICE": "test_service",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = DiscordBotConfig.from_env()

        assert config.token == "test_token"
        assert config.aws_role_arn is None
        assert config.aws_region is None

    def test_missing_token_raises_error(self):
        """Test error when token is missing."""
        with patch.dict(os.environ, {}, clear=True), pytest.raises(
            ValueError, match="DISCORD_TOKEN environment variable is required"
        ):
            DiscordBotConfig.from_env()

    def test_missing_cluster_raises_error(self):
        """Test error when cluster is missing."""
        with patch.dict(os.environ, {"DISCORD_TOKEN": "test"}, clear=True):
            with pytest.raises(
                ValueError, match="ECS_CLUSTER environment variable is required"
            ):
                DiscordBotConfig.from_env()


class TestDNSUpdaterConfig:
    """Test DNS updater configuration."""

    def test_from_env_complete(self):
        """Test configuration with all environment variables."""
        env_vars = {
            "CLOUDFLARE_TOKEN": "test_token",
            "CLOUDFLARE_ZONE_ID": "test_zone",
            "DNS_RECORD_NAME": "mc.example.com",
            "ECS_CLUSTER": "test_cluster",
            "ECS_SERVICE": "test_service",
        }

        with patch.dict(os.environ, env_vars):
            config = DNSUpdaterConfig.from_env()

        assert config.cloudflare_token == "test_token"
        assert config.zone_id == "test_zone"
        assert config.record_name == "mc.example.com"
        assert config.ecs_cluster == "test_cluster"
        assert config.ecs_service == "test_service"

    def test_missing_token_raises_error(self):
        """Test error when Cloudflare token is missing."""
        with patch.dict(os.environ, {}, clear=True), pytest.raises(
            ValueError, match="CLOUDFLARE_TOKEN environment variable is required"
        ):
            DNSUpdaterConfig.from_env()


class TestIdleWatcherConfig:
    """Test idle watcher configuration."""

    def test_from_env_complete(self):
        """Test configuration with all environment variables."""
        env_vars = {
            "ECS_CLUSTER": "test_cluster",
            "ECS_SERVICE": "test_service",
            "RCON_HOST": "mc.example.com",
            "RCON_PORT": "25576",
            "RCON_PASSWORD": "testpass",
            "CHECK_INTERVAL": "120",
            "IDLE_THRESHOLD": "300",
        }

        with patch.dict(os.environ, env_vars):
            config = IdleWatcherConfig.from_env()

        assert config.ecs_cluster == "test_cluster"
        assert config.rcon_host == "mc.example.com"
        assert config.rcon_port == 25576
        assert config.rcon_password == "testpass"
        assert config.check_interval == 120
        assert config.idle_threshold == 300

    def test_from_env_with_defaults(self):
        """Test configuration with default values."""
        env_vars = {
            "ECS_CLUSTER": "test_cluster",
            "ECS_SERVICE": "test_service",
            "RCON_HOST": "mc.example.com",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = IdleWatcherConfig.from_env()

        assert config.rcon_port == 25575
        assert config.rcon_password == ""
        assert config.check_interval == 300
        assert config.idle_threshold == 600

    def test_missing_host_raises_error(self):
        """Test error when RCON host is missing."""
        env_vars = {"ECS_CLUSTER": "test", "ECS_SERVICE": "test"}
        with patch.dict(os.environ, env_vars, clear=True), pytest.raises(
            ValueError, match="RCON_HOST environment variable is required"
        ):
            IdleWatcherConfig.from_env()
