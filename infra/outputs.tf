output "lambda_function_arn" {
  value = aws_lambda_function.cde_recommend.arn
}

output "lambda_function_name" {
  value = aws_lambda_function.cde_recommend.function_name
}

output "api_gateway_url" {
  value = aws_api_gateway_stage.cde_recommend.invoke_url
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.cache.name
}

output "usage_plan_id" {
  value = aws_api_gateway_usage_plan.cde_recommend.id
}
