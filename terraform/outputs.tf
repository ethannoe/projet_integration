output "bucket_name" { value = aws_s3_bucket.transactions.bucket }
output "database_endpoint" { value = aws_db_instance.transactions.address }
