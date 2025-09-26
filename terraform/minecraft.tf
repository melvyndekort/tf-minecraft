# Minecraft ECS Service
resource "aws_ecs_cluster" "minecraft" {
  name = "minecraft-cluster"
}

resource "aws_ecs_task_definition" "minecraft" {
  family                   = "minecraft-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.task_cpu)
  memory                   = tostring(var.task_memory)
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_execution_role.arn
  
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  volume {
    name = "minecraft-data"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.minecraft.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.minecraft.id
        iam             = "DISABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name      = "minecraft"
      image     = "itzg/minecraft-server:stable"
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
        },
        {
          containerPort = 19132
          hostPort      = 19132
          protocol      = "udp"
        }
      ]
      mountPoints = [
        {
          sourceVolume  = "minecraft-data"
          containerPath = "/data"
          readOnly      = false
        }
      ]
      environment = [
        { name = "EULA", value = "TRUE" },
        { name = "TYPE", value = "PAPER" },
        { name = "VERSION", value = "1.21.1" },
        { name = "SERVER_NAME", value = "MelvynMC" },
        { name = "MOTD", value = "Melvyn's MC Server" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.minecraft.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "minecraft"
        }
      }
    },
    {
      name      = "dns-updater"
      image     = "ghcr.io/melvyndekort/dns-updater:latest"
      essential = false
      environment = [
        { name = "CLOUDFLARE_ZONE_ID", value = data.cloudflare_zone.zone.zone_id },
        { name = "CLOUDFLARE_A_RECORD_ID", value = cloudflare_dns_record.minecraft_a.id },
        { name = "CLOUDFLARE_AAAA_RECORD_ID", value = cloudflare_dns_record.minecraft_aaaa.id },
        { name = "DNS_NAME", value = local.fqdn }
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
          "awslogs-group"         = aws_cloudwatch_log_group.minecraft.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "dns-updater"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "minecraft" {
  name                               = "minecraft-service"
  cluster                            = aws_ecs_cluster.minecraft.id
  task_definition                    = aws_ecs_task_definition.minecraft.arn
  desired_count                      = var.desired_count
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
  enable_execute_command             = true

  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
  }

  network_configuration {
    subnets          = [data.aws_subnet.public.id]
    security_groups  = [aws_security_group.minecraft.id]
    assign_public_ip = true
  }

  depends_on = [aws_efs_mount_target.minecraft]
}

resource "aws_cloudwatch_log_group" "minecraft" {
  name              = "/ecs/minecraft"
  retention_in_days = 7
}

# EFS Storage
resource "aws_efs_file_system" "minecraft" {
  availability_zone_name = local.chosen_az
  encrypted              = true
  throughput_mode        = "elastic"
  tags = {
    Name = "minecraft-efs"
  }
}

resource "aws_efs_access_point" "minecraft" {
  file_system_id = aws_efs_file_system.minecraft.id

  posix_user {
    uid = 1000
    gid = 1000
  }

  root_directory {
    path = "/minecraft"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "0755"
    }
  }
}

resource "aws_efs_mount_target" "minecraft" {
  file_system_id  = aws_efs_file_system.minecraft.id
  subnet_id       = data.aws_subnet.public.id
  security_groups = [aws_security_group.efs.id]
}