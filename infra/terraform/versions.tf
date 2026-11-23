terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Estado local por defecto (el archivo .tfstate NO se versiona). Para trabajo en equipo,
  # descomente y cree antes el bucket y la tabla de bloqueo:
  # backend "s3" {
  #   bucket         = "mi-bucket-de-estado"
  #   key            = "stockia/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "mi-tabla-de-bloqueo"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
    }
  }
}
