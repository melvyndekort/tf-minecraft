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
      aws_ssm_parameter.cloudflare_api_token.arn
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "kms:Decrypt"
    ]

    resources = ["*"] # kan specifieker: de KMS key die SSM gebruikt
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
