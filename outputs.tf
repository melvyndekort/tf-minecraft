output "ecs_cluster_id" {
  value = aws_ecs_cluster.minecraft.id
}
output "ecs_service_name" {
  value = aws_ecs_service.minecraft.name
}
output "efs_id" {
  value = aws_efs_file_system.minecraft.id
}
output "dns_name" {
  value = local.fqdn
}

output "discord_bot_role_arn" {
  value = aws_iam_role.discord_bot_role.arn
}

output "discord_bot_access_key" {
  value     = aws_iam_access_key.discord_bot.id
  sensitive = false
}

output "discord_bot_secret_key" {
  value     = aws_iam_access_key.discord_bot.secret
  sensitive = true
}
