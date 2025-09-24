module "temp_ec2" {
  count  = var.create_temp_ec2 ? 1 : 0
  source = "./modules/temp-ec2"

  vpc_id                = data.aws_vpc.vpc.id
  subnet_id             = data.aws_subnet.public.id
  efs_id                = aws_efs_file_system.minecraft.id
  efs_security_group_id = aws_security_group.efs.id
  ssh_public_key        = var.ssh_public_key
}

output "temp_ec2_ip" {
  value = length(module.temp_ec2) > 0 ? module.temp_ec2[0].public_ip : null
}

output "temp_ec2_ssh_command" {
  value = length(module.temp_ec2) > 0 ? module.temp_ec2[0].ssh_command : null
}
