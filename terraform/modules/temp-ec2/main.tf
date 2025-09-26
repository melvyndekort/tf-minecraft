data "aws_region" "current" {}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  
  filter {
    name   = "name"
    values = ["al2023-ami-*-arm64"]
  }
}

resource "aws_security_group" "temp_ec2" {
  name        = "temp-ec2-efs-access"
  description = "Temporary EC2 instance for EFS access"
  vpc_id      = var.vpc_id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "temp-ec2-efs-access"
  }
}

resource "aws_security_group_rule" "efs_from_temp_ec2" {
  type                     = "ingress"
  from_port                = 2049
  to_port                  = 2049
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.temp_ec2.id
  security_group_id        = var.efs_security_group_id
}

resource "aws_key_pair" "temp_key" {
  key_name_prefix = "temp-"
  public_key      = var.ssh_public_key
}

resource "aws_instance" "temp_efs_access" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t4g.nano"
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.temp_ec2.id]
  key_name               = aws_key_pair.temp_key.key_name

  user_data_base64 = base64encode(templatefile("${path.module}/user-data.sh", {
    efs_id = var.efs_id
    region = data.aws_region.current.id
  }))

  tags = {
    Name = "temp-efs-access"
  }
}
