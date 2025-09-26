#!/usr/bin/env python3
import os
import sys
import requests


def get_ecs_task_metadata():
    """Get ECS task metadata for Fargate."""
    try:
        metadata_uri = os.getenv('ECS_CONTAINER_METADATA_URI_V4')
        if not metadata_uri:
            print("Error: ECS_CONTAINER_METADATA_URI_V4 not found")
            return None, None
            
        # Get task metadata
        response = requests.get(f"{metadata_uri}/task", timeout=5)
        response.raise_for_status()
        task_metadata = response.json()
        
        # Extract public IP from network interfaces
        ipv4 = None
        ipv6 = None
        
        for container in task_metadata.get('Containers', []):
            for network in container.get('Networks', []):
                if network.get('NetworkMode') == 'awsvpc':
                    ipv4 = network.get('IPv4Addresses', [None])[0]
                    ipv6_list = network.get('IPv6Addresses', [])
                    ipv6 = ipv6_list[0] if ipv6_list else None
                    break
        
        return ipv4, ipv6
    except requests.RequestException as e:
        print(f"Error getting ECS metadata: {e}")
        return None, None


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
    
    # Get task IPs from ECS metadata
    ipv4, ipv6 = get_ecs_task_metadata()
    
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
