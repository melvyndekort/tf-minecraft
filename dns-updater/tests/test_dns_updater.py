import os
import sys
import pytest
import responses
from unittest.mock import patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dns_updater import get_instance_metadata, update_dns_record, main


@responses.activate
def test_get_instance_metadata_success():
    responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/public-ipv4", body="1.2.3.4")
    assert get_instance_metadata("public-ipv4") == "1.2.3.4"


@responses.activate
def test_get_instance_metadata_failure():
    responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/public-ipv4", status=404)
    assert get_instance_metadata("public-ipv4") is None


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
    "DNS_NAME": "test.example.com"
})
@responses.activate
def test_main_success():
    responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/public-ipv4", body="1.2.3.4")
    responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/ipv6", body="2001:db8::1")
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
@responses.activate
def test_main_no_ipv4_fails():
    responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/public-ipv4", status=404)
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
