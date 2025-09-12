output "ecs_cluster_id" {
  value = aws_ecs_cluster.mc_cluster.id
}
output "ecs_service_name" {
  value = aws_ecs_service.mc_service.name
}
output "efs_id" {
  value = aws_efs_file_system.minecraft.id
}
output "dns_name" {
  value = local.fqdn
}
