resource "aws_iam_role" "ecs_task_execution_role" {
  name               = "ecsTaskExecutionRole-mc"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "ecs_ssm_access" {
  statement {
    effect = "Allow"

    actions = [
      "ssm:GetParameters",
      "ssm:GetParameter",
      "ssm:GetParametersByPath"
    ]

    resources = [
      aws_ssm_parameter.cloudflare_api_token.arn,
      aws_ssm_parameter.discord_webhook_url.arn
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "kms:Decrypt"
    ]

    resources = ["*"]
  }

  # mc-dns-updater permissions
  statement {
    effect = "Allow"
    actions = [
      "ecs:DescribeTasks",
      "ecs:ListTasks",
      "ec2:DescribeNetworkInterfaces"
    ]
    resources = ["*"]
  }

  # mc-idle-watcher permissions
  statement {
    effect = "Allow"
    actions = [
      "ecs:UpdateService",
      "ecs:DescribeServices"
    ]
    resources = [aws_ecs_service.minecraft.arn]
  }

  # ECS Exec permissions
  statement {
    effect = "Allow"
    actions = [
      "ssmmessages:CreateControlChannel",
      "ssmmessages:CreateDataChannel",
      "ssmmessages:OpenControlChannel",
      "ssmmessages:OpenDataChannel"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "ecs_ssm_access" {
  name   = "ecs-ssm-access"
  policy = data.aws_iam_policy_document.ecs_ssm_access.json
}

resource "aws_iam_role_policy_attachment" "ecs_ssm_access" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.ecs_ssm_access.arn
}

# Discord bot IAM user
resource "aws_iam_user" "discord_bot" {
  name = "mc-discord-bot"
}

resource "aws_iam_access_key" "discord_bot" {
  user = aws_iam_user.discord_bot.name
}

# Discord bot IAM role
resource "aws_iam_role" "discord_bot_role" {
  name               = "mc-discord-bot-role"
  assume_role_policy = data.aws_iam_policy_document.discord_bot_assume_role.json
}

data "aws_iam_policy_document" "discord_bot_assume_role" {
  statement {
    principals {
      type        = "AWS"
      identifiers = [aws_iam_user.discord_bot.arn]
    }
    actions = ["sts:AssumeRole"]
  }
}

# Discord bot ECS permissions
data "aws_iam_policy_document" "discord_bot_ecs" {
  statement {
    effect = "Allow"
    actions = [
      "ecs:DescribeServices",
      "ecs:UpdateService",
      "ecs:DescribeTasks",
      "ecs:ListTasks"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "ec2:DescribeNetworkInterfaces"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "discord_bot_ecs" {
  name   = "mc-discord-bot-ecs"
  policy = data.aws_iam_policy_document.discord_bot_ecs.json
}

resource "aws_iam_role_policy_attachment" "discord_bot_ecs" {
  role       = aws_iam_role.discord_bot_role.name
  policy_arn = aws_iam_policy.discord_bot_ecs.arn
}
