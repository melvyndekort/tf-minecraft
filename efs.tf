# --- EFS file system for persistent server data ---
resource "aws_efs_file_system" "minecraft" {
  availability_zone_name = local.chosen_az
  encrypted              = true
  throughput_mode        = "elastic"
  tags = {
    Name = "mc-efs"
  }
}

resource "aws_efs_access_point" "mc_ap" {
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

resource "aws_efs_mount_target" "target" {
  file_system_id  = aws_efs_file_system.minecraft.id
  subnet_id       = data.aws_subnet.public.id
  security_groups = [aws_security_group.efs_sg.id]
}
