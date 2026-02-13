resource "aws_dynamodb_table" "cache" {
  name         = "cde_recommendation_cache_${var.environment}"
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
    Name        = "cde-recommendation-cache"
    Environment = var.environment
  }
}
