output "public_ip" {
  value = aws_instance.temp_efs_access.public_ip
}

output "ssh_command" {
  value = "ssh ec2-user@${aws_instance.temp_efs_access.public_ip}"
}
