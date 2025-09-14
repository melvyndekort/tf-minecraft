#!/bin/bash
set -e

# Create AWS config with environment variables
cat > /home/appuser/.aws/config << EOF
[profile botrole]
role_arn = ${AWS_ROLE_ARN}
source_profile = default
region = ${AWS_DEFAULT_REGION}
EOF

exec "$@"
