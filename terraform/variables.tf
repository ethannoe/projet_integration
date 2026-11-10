variable "aws_region" {
  type    = string
  default = "eu-west-3"
}

variable "project_name" {
  type    = string
  default = "transactions-pipeline"
}

variable "db_username" {
  type      = string
  sensitive = true
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "allowed_cidr" {
  type        = string
  description = "CIDR autorisé à joindre PostgreSQL"
}
