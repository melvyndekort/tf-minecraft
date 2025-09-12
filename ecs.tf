# --- ECS cluster ---
resource "aws_ecs_cluster" "mc_cluster" {
  name = "mc-ecs-cluster"
}

resource "aws_ecs_task_definition" "mc_task" {
  family                   = "mc-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.task_cpu)
  memory                   = tostring(var.task_memory)
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_execution_role.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  volume {
    name = "mc-data"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.minecraft.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.mc_ap.id
        iam             = "DISABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name      = "minecraft"
      image     = "itzg/minecraft-server:latest"
      essential = true
      portMappings = [
        {
          containerPort = 25565
          hostPort      = 25565
          protocol      = "tcp"
        },
        {
          containerPort = 25565
          hostPort      = 25565
          protocol      = "udp"
        }
      ]
      mountPoints = [
        {
          sourceVolume  = "mc-data"
          containerPath = "/data"
          readOnly      = false
        }
      ]
      environment = [
        { name = "EULA", value = "TRUE" },
        { name = "TYPE", value = "PAPER" },
        { name = "SERVER_NAME", value = "MelvynMC" },
        { name = "MOTD", value = "Melvyn's MC Server" },
      ]
      linuxParameters = {}
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "minecraft"
        }
      }
    },
    {
      name      = "cloudflare-dns-updater"
      image     = "alpine:latest"
      essential = false
      environment = [
        { name = "CLOUDFLARE_ZONE_ID",        value = data.cloudflare_zone.zone.zone_id },
        { name = "CLOUDFLARE_A_RECORD_ID",    value = cloudflare_dns_record.mc_a.id },
        { name = "CLOUDFLARE_AAAA_RECORD_ID", value = cloudflare_dns_record.mc_aaaa.id },
        { name = "DNS_NAME",                  value = local.fqdn }
      ]
      secrets = [
        {
          name      = "CLOUDFLARE_API_TOKEN"
          valueFrom = aws_ssm_parameter.cloudflare_api_token.arn
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "dns-updater"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "mc_service" {
  name                               = "mc-service"
  cluster                            = aws_ecs_cluster.mc_cluster.id
  task_definition                    = aws_ecs_task_definition.mc_task.arn
  desired_count                      = var.desired_count
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  enable_execute_command = true

  network_configuration {
    subnets          = [data.aws_subnet.public.id]
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  depends_on = [aws_efs_mount_target.target]
}

resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/mc-task"
  retention_in_days = 7
}
