resource "aws_dynamodb_table" "cache" {
  name         = "${var.project_name}-cache-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cache_key"

  attribute {
    name = "cache_key"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-cache"
    Environment = var.environment
  }
}
