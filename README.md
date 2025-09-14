# tf-minecraft

A scalable Minecraft server infrastructure on AWS ECS with Discord bot integration for remote server management.

## 🎮 Features

- **Serverless Minecraft Server**: Runs on AWS ECS Fargate with automatic scaling
- **Discord Bot Integration**: Start, stop, and check server status via Discord commands
- **Dynamic DNS**: Automatic IP updates via Cloudflare DNS
- **Persistent Storage**: EFS-backed world data that persists across restarts
- **Cost Optimized**: Pay only when the server is running

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Discord Bot   │───▶│   AWS ECS Task   │───▶│  Minecraft      │
│   (Commands)    │    │   (Fargate)      │    │  Server         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   DNS Updater    │    │   EFS Storage   │
                       │   (Cloudflare)   │    │   (Persistent)  │
                       └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform >= 1.0
- Docker and Docker Compose
- Cloudflare account with API token
- Discord bot token

### 1. Deploy Infrastructure

```bash
# Clone the repository
git clone <repository-url>
cd tf-minecraft

# Configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Deploy infrastructure
terraform init
terraform plan
terraform apply
```

### 2. Setup Discord Bot

```bash
cd discord-bot

# Create environment file
cat > .env << EOF
DISCORD_TOKEN=your_discord_bot_token_here
ECS_CLUSTER=your_ecs_cluster_name
ECS_SERVICE=your_ecs_service_name
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/YourBotRole
AWS_DEFAULT_REGION=eu-west-1
AWS_CREDENTIALS_PATH=/path/to/your/aws/credentials
EOF

# Edit .env with your actual values

# Run the bot
docker-compose up -d
```

### 3. Discord Commands

Once the bot is running, use these slash commands in Discord:

- `/server-start` - Start the Minecraft server
- `/server-stop` - Stop the Minecraft server  
- `/server-status` - Check current server status

## 📁 Project Structure

```
tf-minecraft/
├── discord-bot/          # Discord bot for server management
│   ├── src/bot.py       # Bot implementation
│   ├── tests/           # Unit tests
│   ├── Dockerfile       # Container configuration
│   └── docker-compose.yml
├── dns-updater/         # Dynamic DNS updater
├── *.tf                 # Terraform infrastructure code
└── .github/workflows/   # CI/CD pipelines
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|----------|
| `DISCORD_TOKEN` | Discord bot token | `MTQx...` |
| `ECS_CLUSTER` | ECS cluster name | `minecraft-cluster` |
| `ECS_SERVICE` | ECS service name | `minecraft-service` |
| `AWS_ROLE_ARN` | IAM role for bot | `arn:aws:iam::123:role/discord-bot-role` |
| `AWS_DEFAULT_REGION` | AWS region | `us-east-1` |

### Terraform Variables

Key variables in `terraform.tfvars`:

```hcl
region = "us-east-1"
dns_zone = "example.com"
dns_record = "minecraft"
task_cpu = 2048
task_memory = 4096
desired_count = 0  # Start with server stopped
```

## 🔒 Security

- Discord bot uses IAM role assumption with minimal ECS permissions
- EFS encryption at rest and in transit
- Security groups restrict access to Minecraft port only
- Secrets managed via AWS SSM Parameter Store

## 💰 Cost Optimization

- Server runs only when needed (desired_count = 0 by default)
- Fargate Spot pricing for cost savings
- EFS Intelligent Tiering for storage optimization
- CloudWatch logs with 7-day retention

## 🛠️ Development

### Discord Bot Development

```bash
cd discord-bot

# Install dependencies
poetry install

# Run tests
poetry run pytest

# Local development
poetry run python src/bot.py
```

### Infrastructure Changes

```bash
# Plan changes
terraform plan

# Apply changes
terraform apply

# Destroy infrastructure
terraform destroy
```

## 📊 Monitoring

- CloudWatch logs for all services
- Discord bot provides real-time status updates
- ECS service metrics available in AWS Console

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

**Discord bot not responding:**
- Check bot token is valid
- Verify AWS credentials are configured
- Check CloudWatch logs for errors

**Server won't start:**
- Verify ECS service exists
- Check IAM permissions
- Review ECS task logs

**DNS not updating:**
- Verify Cloudflare API token
- Check DNS record IDs in Terraform

### Getting Help

- Check CloudWatch logs: `/ecs/minecraft`
- Review Discord bot logs: `docker-compose logs discord-bot`
- AWS ECS Console for service status
