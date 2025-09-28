#!/usr/bin/env python3
import os
import sys
import requests
import boto3


def get_task_public_ips():
    """Get public IP addresses from ECS task using AWS APIs."""
    try:
        # Get task metadata to find task ARN
        metadata_uri = os.getenv('ECS_CONTAINER_METADATA_URI_V4')
        if not metadata_uri:
            print("Error: ECS_CONTAINER_METADATA_URI_V4 not found")
            return None, None
            
        response = requests.get(f"{metadata_uri}/task", timeout=5)
        response.raise_for_status()
        task_metadata = response.json()
        
        task_arn = task_metadata.get('TaskARN')
        if not task_arn:
            print("Error: Could not get task ARN from metadata")
            return None, None
        
        # Extract cluster name and task ID from ARN
        cluster_name = task_arn.split('/')[1]
        task_id = task_arn.split('/')[-1]
        
        # Use ECS client to get task details
        ecs = boto3.client('ecs')
        response = ecs.describe_tasks(
            cluster=cluster_name,
            tasks=[task_id]
        )
        
        if not response['tasks']:
            print("Error: Task not found")
            return None, None
            
        task = response['tasks'][0]
        
        # Get ENI ID from task attachments
        eni_id = None
        for attachment in task.get('attachments', []):
            if attachment['type'] == 'ElasticNetworkInterface':
                for detail in attachment['details']:
                    if detail['name'] == 'networkInterfaceId':
                        eni_id = detail['value']
                        break
        
        if not eni_id:
            print("Error: Could not find ENI ID")
            return None, None
        
        # Get public IPs from ENI
        ec2 = boto3.client('ec2')
        response = ec2.describe_network_interfaces(
            NetworkInterfaceIds=[eni_id]
        )
        
        if not response['NetworkInterfaces']:
            print("Error: ENI not found")
            return None, None
            
        eni = response['NetworkInterfaces'][0]
        
        ipv4 = None
        ipv6 = None
        
        # Get IPv4
        if eni.get('Association', {}).get('PublicIp'):
            ipv4 = eni['Association']['PublicIp']
        
        # Get IPv6
        for ipv6_addr in eni.get('Ipv6Addresses', []):
            ipv6 = ipv6_addr['Ipv6Address']
            break
            
        return ipv4, ipv6
        
    except Exception as e:
        print(f"Error getting task public IPs: {e}")
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
    
    # Get task IPs from AWS APIs
    ipv4, ipv6 = get_task_public_ips()
    
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
