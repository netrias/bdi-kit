terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    key     = "cde-recommend/terraform.tfstate"
    encrypt = true
    # bucket, dynamodb_table, region supplied via -backend-config flags
  }
}

provider "aws" {
  region = var.aws_region
}
