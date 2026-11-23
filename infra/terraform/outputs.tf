output "app_url" {
  description = "Dirección de la aplicación (después de subir la imagen)."
  value       = "${local.https ? "https" : "http"}://${aws_lb.app.dns_name}"
}

output "ecr_repository_url" {
  description = "Repositorio donde subir la imagen con docker push."
  value       = aws_ecr_repository.app.repository_url
}

output "push_commands" {
  description = "Comandos para construir y subir la imagen."
  value       = <<-EOT
    aws ecr get-login-password --region ${var.region} | docker login --username AWS --password-stdin ${split("/", aws_ecr_repository.app.repository_url)[0]}
    docker build --target app -t ${aws_ecr_repository.app.repository_url}:${var.image_tag} .
    docker push ${aws_ecr_repository.app.repository_url}:${var.image_tag}
    aws ecs update-service --region ${var.region} --cluster ${aws_ecs_cluster.main.name} --service ${aws_ecs_service.app.name} --force-new-deployment
  EOT
}
