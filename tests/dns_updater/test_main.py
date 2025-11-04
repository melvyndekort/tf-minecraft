import os
import pytest
import responses
from unittest.mock import patch, MagicMock

from minecraft_tools.dns_updater.main import get_task_public_ips, update_dns_record, main


@responses.activate
@patch('minecraft_tools.dns_updater.main.boto3')
def test_get_task_public_ips_success(mock_boto3):
    metadata_uri = "http://169.254.170.2/v4/metadata"
    responses.add(responses.GET, f"{metadata_uri}/task", json={
        "TaskARN": "arn:aws:ecs:us-east-1:123456789012:task/cluster-name/task-id"
    })
    
    # Mock ECS client
    mock_ecs = MagicMock()
    mock_ecs.describe_tasks.return_value = {
        'tasks': [{
            'attachments': [{
                'type': 'ElasticNetworkInterface',
                'details': [{'name': 'networkInterfaceId', 'value': 'eni-123'}]
            }]
        }]
    }
    
    # Mock EC2 client
    mock_ec2 = MagicMock()
    mock_ec2.describe_network_interfaces.return_value = {
        'NetworkInterfaces': [{
            'Association': {'PublicIp': '1.2.3.4'},
            'Ipv6Addresses': [{'Ipv6Address': '2001:db8::1'}]
        }]
    }
    
    mock_boto3.client.side_effect = lambda service: mock_ecs if service == 'ecs' else mock_ec2
    
    with patch.dict(os.environ, {"ECS_CONTAINER_METADATA_URI_V4": metadata_uri}):
        ipv4, ipv6 = get_task_public_ips()
        assert ipv4 == "1.2.3.4"
        assert ipv6 == "2001:db8::1"


def test_get_task_public_ips_no_uri():
    with patch.dict(os.environ, {}, clear=True):
        ipv4, ipv6 = get_task_public_ips()
        assert ipv4 is None
        assert ipv6 is None


@responses.activate
def test_update_dns_record_success():
    responses.add(responses.PUT, "https://api.cloudflare.com/client/v4/zones/zone123/dns_records/record123", json={"success": True})
    assert update_dns_record("zone123", "record123", "A", "test.example.com", "1.2.3.4", "token123") is True


@responses.activate
def test_update_dns_record_failure():
    responses.add(responses.PUT, "https://api.cloudflare.com/client/v4/zones/zone123/dns_records/record123", status=400)
    assert update_dns_record("zone123", "record123", "A", "test.example.com", "1.2.3.4", "token123") is False


def test_main_missing_env_vars():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


@patch.dict(os.environ, {
    "CLOUDFLARE_ZONE_ID": "zone123",
    "CLOUDFLARE_A_RECORD_ID": "a_record123", 
    "CLOUDFLARE_AAAA_RECORD_ID": "aaaa_record123",
    "CLOUDFLARE_API_TOKEN": "token123",
    "DNS_NAME": "test.example.com",
    "ECS_CONTAINER_METADATA_URI_V4": "http://169.254.170.2/v4/metadata"
})
@responses.activate
@patch('minecraft_tools.dns_updater.main.boto3')
def test_main_success(mock_boto3):
    responses.add(responses.GET, "http://169.254.170.2/v4/metadata/task", json={
        "TaskARN": "arn:aws:ecs:us-east-1:123456789012:task/cluster-name/task-id"
    })
    
    mock_ecs = MagicMock()
    mock_ecs.describe_tasks.return_value = {
        'tasks': [{
            'attachments': [{
                'type': 'ElasticNetworkInterface',
                'details': [{'name': 'networkInterfaceId', 'value': 'eni-123'}]
            }]
        }]
    }
    
    mock_ec2 = MagicMock()
    mock_ec2.describe_network_interfaces.return_value = {
        'NetworkInterfaces': [{
            'Association': {'PublicIp': '1.2.3.4'},
            'Ipv6Addresses': [{'Ipv6Address': '2001:db8::1'}]
        }]
    }
    
    mock_boto3.client.side_effect = lambda service: mock_ecs if service == 'ecs' else mock_ec2
    
    responses.add(responses.PUT, "https://api.cloudflare.com/client/v4/zones/zone123/dns_records/a_record123", json={"success": True})
    responses.add(responses.PUT, "https://api.cloudflare.com/client/v4/zones/zone123/dns_records/aaaa_record123", json={"success": True})
    main()  # Should not raise


@patch.dict(os.environ, {
    "CLOUDFLARE_ZONE_ID": "zone123",
    "CLOUDFLARE_A_RECORD_ID": "a_record123",
    "CLOUDFLARE_AAAA_RECORD_ID": "aaaa_record123", 
    "CLOUDFLARE_API_TOKEN": "token123",
    "DNS_NAME": "test.example.com"
})
def test_main_no_ipv4_fails():
    with patch.dict(os.environ, {"ECS_CONTAINER_METADATA_URI_V4": ""}, clear=False):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
