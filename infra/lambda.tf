resource "aws_lambda_function" "cde_recommend" {
  function_name = "cde-recommend-${var.environment}"
  role          = aws_iam_role.lambda.arn
  handler       = "cde_recommend.handler.handler"
  runtime       = "python3.12"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size

  # Placeholder — real deployment uses CI/CD pipeline to upload package
  filename = "lambda.zip"

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DB_HOST          = var.db_host
      DB_NAME          = var.db_name
      DB_PORT          = var.db_port
      DB_USER          = var.db_user
      DB_PASSWORD      = var.db_password
      DB_SSLMODE       = "require"
      OPENAI_API_KEY   = var.openai_api_key
      CACHE_TABLE_NAME = aws_dynamodb_table.cache.name
      AWS_REGION       = var.aws_region
    }
  }

  tags = {
    Name        = "cde-recommend"
    Environment = var.environment
  }
}
