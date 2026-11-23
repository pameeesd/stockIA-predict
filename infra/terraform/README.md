# Infraestructura en AWS (Terraform) — escrita, NO desplegada

Este código describe cómo publicar la app en AWS. **No se ha aplicado nunca** (`terraform apply` no se ejecutó): se comprobó el formato (`terraform fmt`) y la validez (`terraform validate`), pero no un `plan` ni un despliegue real, porque requieren credenciales de AWS y generan costo.

## Qué crea

```text
Internet ──► ALB (HTTP/HTTPS, solo CIDR permitidos) ──► ECS Fargate (1 tarea, contenedor `app`, puerto 8501)
                                                         │
                          ECR (imagen) ◄─────────────────┘      CloudWatch Logs
```

| Archivo | Recursos |
|---|---|
| `network.tf` | VPC, 2 subredes públicas, internet gateway, grupos de seguridad (la app solo acepta tráfico del balanceador) |
| `alb.tf` | Balanceador, target group con chequeo en `/_stcore/health`, listeners HTTP / HTTPS opcional |
| `ecr.tf` | Repositorio de imágenes con escaneo al subir y conservación de las 10 más recientes |
| `ecs.tf` | Clúster, definición de tarea, servicio Fargate, rol de ejecución mínimo, registros en CloudWatch |
| `outputs.tf` | URL de la app, URL del repositorio y los comandos para subir la imagen |

## Decisiones de diseño

- **Sin NAT Gateway:** las tareas van en subredes públicas con IP pública, pero su grupo de seguridad solo admite el tráfico del balanceador. Evita ~USD 30/mes de NAT.
- **Sin valor abierto por defecto:** `allowed_cidrs` es obligatorio, porque la app tiene acceso simulado (sin autenticación real). Debe restringirse a su IP.
- **Una sola tarea** (`desired_count` ≤ 1, validado): la base SQLite es local a la tarea; con dos habría dos historiales distintos.
- **Historial efímero:** SQLite vive en el disco de la tarea y se pierde al reiniciarla. Para persistirlo habría que montar EFS (con cuidado: SQLite sobre NFS tiene limitaciones de bloqueo) o migrar el historial a una base administrada (RDS). No se incluye porque excede una prueba de concepto.
- **HTTPS opcional:** con `certificate_arn` (ACM) se habilita 443 y HTTP redirige. Sin él, solo HTTP: aceptable para una demostración con datos públicos, no para datos reales.
- **Privilegios mínimos:** la app no llama a AWS, así que solo existe el rol de ejecución estándar de ECS (descargar imagen y escribir registros).

## Costo aproximado (referencial, verifique en la calculadora de AWS)

El balanceador y la tarea Fargate (0,5 vCPU, 1 GB) funcionan de forma continua: del orden de **USD 30–40 al mes** en `us-east-1`, más pequeños cargos de transferencia, registros y ECR. `desired_count = 0` detiene el cómputo pero el balanceador sigue cobrando; para dejar de pagar hay que destruir todo.

## Cómo se desplegaría (si decide hacerlo)

Requiere Terraform ≥ 1.5, AWS CLI con credenciales y Docker.

```powershell
cd infra/terraform
copy terraform.tfvars.example terraform.tfvars   # edite allowed_cidrs con su IP
terraform init
terraform plan
terraform apply -target=aws_ecr_repository.app   # crea primero el repositorio
terraform output -raw push_commands              # ejecute esos comandos desde la raíz del repo
terraform apply                                  # crea el resto; luego terraform output app_url
```

Para eliminar todo y dejar de pagar: `terraform destroy`.

## Fuera de alcance (a propósito)

Dominio propio y DNS, autenticación real (por ejemplo Cognito en el balanceador), WAF, alarmas, almacenamiento persistente, autoescalado y despliegue continuo desde GitHub Actions. Son los siguientes pasos si la app pasara de prueba de concepto a servicio.
