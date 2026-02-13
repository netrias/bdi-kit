variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "project_name" {
  type    = string
  default = "cde-recommend"
}

variable "db_host" {
  type = string
}

variable "db_name" {
  type    = string
  default = "data_model_store"
}

variable "db_port" {
  type    = string
  default = "5432"
}

variable "db_user" {
  type      = string
  sensitive = true
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "openai_api_key" {
  type      = string
  sensitive = true
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "security_group_ids" {
  type = list(string)
}

variable "lambda_timeout" {
  type    = number
  default = 300
}

variable "lambda_memory_size" {
  type    = number
  default = 512
}
