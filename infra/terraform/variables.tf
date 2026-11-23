variable "region" {
  description = "Región de AWS."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Prefijo para nombrar los recursos."
  type        = string
  default     = "stockia"
}

variable "image_tag" {
  description = "Etiqueta de la imagen en ECR (la que se sube con docker push)."
  type        = string
  default     = "latest"
}

variable "allowed_cidrs" {
  description = "Rangos CIDR que pueden acceder a la app. La app tiene acceso simulado (sin autenticación real): restrinja esto a su IP, por ejemplo [\"203.0.113.7/32\"]."
  type        = list(string)

  validation {
    condition     = length(var.allowed_cidrs) > 0
    error_message = "Indique al menos un CIDR; no hay valor por defecto abierto a Internet a propósito."
  }
}

variable "certificate_arn" {
  description = "ARN de un certificado ACM para habilitar HTTPS. Vacío = solo HTTP (no recomendado fuera de una demostración)."
  type        = string
  default     = ""
}

variable "task_cpu" {
  description = "CPU de la tarea Fargate (unidades)."
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Memoria de la tarea Fargate (MiB)."
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Número de tareas. Mantener en 1: la base SQLite es local a cada tarea. Use 0 para pausar el cómputo."
  type        = number
  default     = 1

  validation {
    condition     = var.desired_count <= 1
    error_message = "Con SQLite local no se admite más de 1 tarea (cada una tendría su propio historial)."
  }
}

variable "log_retention_days" {
  description = "Días de retención de los registros en CloudWatch."
  type        = number
  default     = 14
}
