#!/usr/bin/env python3
import os
import sys
import requests


def get_instance_metadata(path):
    """Get EC2 instance metadata."""
    try:
        response = requests.get(f"http://169.254.169.254/latest/meta-data/{path}", timeout=5)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error getting metadata {path}: {e}")
        return None


def update_dns_record(zone_id, record_id, record_type, name, content, api_token):
    """Update Cloudflare DNS record."""
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    data = {
        "type": record_type,
        "name": name,
        "content": content,
        "ttl": 120,
        "proxied": False
    }
    
    try:
        response = requests.put(url, json=data, headers=headers)
        response.raise_for_status()
        print(f"Updated {record_type} record: {name} -> {content}")
    except requests.RequestException as e:
        print(f"Error updating {record_type} record: {e}")
        return False
    return True


def main():
    # Get required environment variables
    required_vars = [
        "CLOUDFLARE_ZONE_ID",
        "CLOUDFLARE_A_RECORD_ID", 
        "CLOUDFLARE_AAAA_RECORD_ID",
        "CLOUDFLARE_API_TOKEN",
        "DNS_NAME"
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            print(f"Error: {var} environment variable not set")
            sys.exit(1)
    
    # Get instance IPs
    ipv4 = get_instance_metadata("public-ipv4")
    ipv6 = get_instance_metadata("ipv6")
    
    if not ipv4:
        print("Error: Could not get IPv4 address")
        sys.exit(1)
    
    # Update DNS records
    success = True
    success &= update_dns_record(
        os.getenv("CLOUDFLARE_ZONE_ID"),
        os.getenv("CLOUDFLARE_A_RECORD_ID"),
        "A",
        os.getenv("DNS_NAME"),
        ipv4,
        os.getenv("CLOUDFLARE_API_TOKEN")
    )
    
    if ipv6:
        success &= update_dns_record(
            os.getenv("CLOUDFLARE_ZONE_ID"),
            os.getenv("CLOUDFLARE_AAAA_RECORD_ID"),
            "AAAA",
            os.getenv("DNS_NAME"),
            ipv6,
            os.getenv("CLOUDFLARE_API_TOKEN")
        )
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
