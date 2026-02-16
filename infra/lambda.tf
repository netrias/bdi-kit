resource "aws_lambda_function" "cde_recommend" {
  function_name    = "${var.project_name}-${var.environment}"
  role             = aws_iam_role.lambda.arn
  handler          = "cde_recommend.handler.handler"
  runtime          = "python3.12"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size
  filename         = "${path.module}/../build/lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/../build/lambda.zip")

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = var.security_group_ids
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
    }
  }

  tags = {
    Name        = var.project_name
    Environment = var.environment
  }
}
