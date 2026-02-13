output "lambda_function_arn" {
  value = aws_lambda_function.cde_recommend.arn
}

output "lambda_function_name" {
  value = aws_lambda_function.cde_recommend.function_name
}

output "api_gateway_url" {
  value = aws_apigatewayv2_stage.default.invoke_url
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.cache.name
}
