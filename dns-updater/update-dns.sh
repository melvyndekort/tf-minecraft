#!/bin/sh
set -e

IPV4=$(curl -s http://169.254.170.2/v2/metadata | jq -r '.Containers[0].Networks[0].IPv4Addresses[0]')
IPV6=$(curl -s http://169.254.170.2/v2/metadata | jq -r '.Containers[0].Networks[0].IPv6Addresses[0]')

# Update A record
curl -s -X PUT \
  "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${CLOUDFLARE_A_RECORD_ID}" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "{\"type\":\"A\",\"name\":\"${DNS_NAME}\",\"content\":\"${IPV4}\",\"ttl\":120,\"proxied\":false}"

# Update AAAA record
curl -s -X PUT \
  "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${CLOUDFLARE_AAAA_RECORD_ID}" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "{\"type\":\"AAAA\",\"name\":\"${DNS_NAME}\",\"content\":\"${IPV6}\",\"ttl\":120,\"proxied\":false}"

