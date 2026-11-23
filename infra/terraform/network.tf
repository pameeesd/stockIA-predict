data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${var.project}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project}-igw" }
}

# Subredes públicas sin NAT Gateway (ahorra unos USD 30/mes). Las tareas reciben IP pública
# pero su grupo de seguridad solo admite tráfico desde el balanceador.
resource "aws_subnet" "public" {
  count                   = length(local.azs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.project}-public-${local.azs[count.index]}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${var.project}-public" }
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "alb" {
  name        = "${var.project}-alb"
  description = "Acceso al balanceador desde los CIDR permitidos"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${var.project}-alb" }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  count             = length(var.allowed_cidrs)
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = var.allowed_cidrs[count.index]
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
  description       = "HTTP"
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  count             = var.certificate_arn == "" ? 0 : length(var.allowed_cidrs)
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = var.allowed_cidrs[count.index]
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  description       = "HTTPS"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_app" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = 8501
  to_port                      = 8501
  ip_protocol                  = "tcp"
  description                  = "Hacia la app"
}

resource "aws_security_group" "app" {
  name        = "${var.project}-app"
  description = "App Streamlit: solo trafico desde el balanceador"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${var.project}-app" }
}

resource "aws_vpc_security_group_ingress_rule" "app_from_alb" {
  security_group_id            = aws_security_group.app.id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 8501
  to_port                      = 8501
  ip_protocol                  = "tcp"
  description                  = "Desde el balanceador"
}

# Salida a Internet para descargar la imagen de ECR y enviar registros.
resource "aws_vpc_security_group_egress_rule" "app_out" {
  security_group_id = aws_security_group.app.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
  description       = "Salida (ECR, CloudWatch)"
}
