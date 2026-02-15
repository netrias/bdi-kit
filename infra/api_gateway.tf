# REST API for CDE recommendation — Lambda proxy integration with API key auth.
# Key association is handled by scripts/associate_api_key.py, not Terraform.

resource "aws_api_gateway_rest_api" "cde_recommend" {
  name        = "${var.project_name}-${var.environment}"
  description = "CDE Recommendation API (direct Lambda)"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}"
    Environment = var.environment
  }
}

# /recommend resource
resource "aws_api_gateway_resource" "recommend" {
  rest_api_id = aws_api_gateway_rest_api.cde_recommend.id
  parent_id   = aws_api_gateway_rest_api.cde_recommend.root_resource_id
  path_part   = "recommend"
}

# POST /recommend — requires API key
resource "aws_api_gateway_method" "recommend_post" {
  rest_api_id      = aws_api_gateway_rest_api.cde_recommend.id
  resource_id      = aws_api_gateway_resource.recommend.id
  http_method      = "POST"
  authorization    = "NONE"
  api_key_required = true
}

# Lambda proxy integration
resource "aws_api_gateway_integration" "lambda" {
  rest_api_id             = aws_api_gateway_rest_api.cde_recommend.id
  resource_id             = aws_api_gateway_resource.recommend.id
  http_method             = aws_api_gateway_method.recommend_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.cde_recommend.invoke_arn
}

# Deployment — redeploy when any route/integration changes
resource "aws_api_gateway_deployment" "cde_recommend" {
  rest_api_id = aws_api_gateway_rest_api.cde_recommend.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.recommend.id,
      aws_api_gateway_method.recommend_post.id,
      aws_api_gateway_integration.lambda.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.lambda,
  ]
}

# Stage
resource "aws_api_gateway_stage" "cde_recommend" {
  deployment_id = aws_api_gateway_deployment.cde_recommend.id
  rest_api_id   = aws_api_gateway_rest_api.cde_recommend.id
  stage_name    = var.environment

  tags = {
    Name        = "${var.project_name}-${var.environment}-stage"
    Environment = var.environment
  }
}

# CloudWatch logging
resource "aws_api_gateway_method_settings" "cde_recommend" {
  rest_api_id = aws_api_gateway_rest_api.cde_recommend.id
  stage_name  = aws_api_gateway_stage.cde_recommend.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled    = true
    logging_level      = "ERROR"
    data_trace_enabled = false
  }
}

# Usage plan — key association handled by minting script, not Terraform
resource "aws_api_gateway_usage_plan" "cde_recommend" {
  name        = "${var.project_name}-${var.environment}"
  description = "Usage plan for CDE recommendation (direct Lambda)"

  api_stages {
    api_id = aws_api_gateway_rest_api.cde_recommend.id
    stage  = aws_api_gateway_stage.cde_recommend.stage_name
  }

  throttle_settings {
    burst_limit = 10
    rate_limit  = 5
  }

  quota_settings {
    limit  = 10000
    period = "MONTH"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-plan"
    Environment = var.environment
  }
}

# Allow API Gateway to invoke the Lambda
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cde_recommend.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.cde_recommend.execution_arn}/*/*"
}
