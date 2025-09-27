# Network Data Sources
data "aws_availability_zones" "available" {
  state = "available"
}

resource "random_shuffle" "az" {
  input        = data.aws_availability_zones.available.names
  result_count = 1
}

locals {
  chosen_az = random_shuffle.az.result[0]
}

data "aws_vpc" "vpc" {
  filter {
    name   = "is-default"
    values = ["false"]
  }
}

data "aws_subnet" "public" {
  vpc_id = data.aws_vpc.vpc.id

  filter {
    name   = "availability-zone"
    values = [local.chosen_az]
  }

  filter {
    name   = "tag:Tier"
    values = ["Public"]
  }
}

# Security Groups
resource "aws_security_group" "minecraft" {
  name        = "minecraft-sg"
  description = "Security group for Minecraft ECS tasks"
  vpc_id      = data.aws_vpc.vpc.id

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description      = "Minecraft Java"
    from_port        = 25565
    to_port          = 25565
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description      = "Geyser Bedrock"
    from_port        = 19132
    to_port          = 19132
    protocol         = "udp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description      = "Ping"
    from_port        = 8
    to_port          = 0
    protocol         = "icmp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "minecraft-sg"
  }
}

resource "aws_security_group" "efs" {
  name        = "minecraft-efs-sg"
  description = "Security group for EFS access"
  vpc_id      = data.aws_vpc.vpc.id

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "minecraft-efs-sg"
  }
}

resource "aws_security_group_rule" "efs_from_minecraft" {
  type                     = "ingress"
  from_port                = 2049
  to_port                  = 2049
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.minecraft.id
  security_group_id        = aws_security_group.efs.id
}
