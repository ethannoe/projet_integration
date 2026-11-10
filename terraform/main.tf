resource "aws_s3_bucket" "transactions" {
  bucket = "${var.project_name}-${data.aws_caller_identity.current.account_id}"
  force_destroy = false
}
resource "aws_s3_bucket_versioning" "transactions" {
  bucket = aws_s3_bucket.transactions.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "transactions" {
  bucket = aws_s3_bucket.transactions.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" } }
}
resource "aws_db_subnet_group" "transactions" {
  name = "${var.project_name}-db"
  subnet_ids = var.private_subnet_ids
}
resource "aws_security_group" "postgres" {
  name = "${var.project_name}-postgres"
  description = "Accès PostgreSQL depuis le CIDR de l'application"
  vpc_id = var.vpc_id
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_db_instance" "transactions" {
  identifier = var.project_name
  engine = "postgres"
  engine_version = "16"
  instance_class = "db.t4g.micro"
  allocated_storage = 20
  storage_encrypted = true
  db_name = "transactions"
  username = var.db_username
  password = var.db_password
  db_subnet_group_name = aws_db_subnet_group.transactions.name
  vpc_security_group_ids = [aws_security_group.postgres.id]
  publicly_accessible = false
  skip_final_snapshot = true
}
data "aws_caller_identity" "current" {}
