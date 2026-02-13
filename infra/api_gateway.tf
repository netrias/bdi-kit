resource "aws_apigatewayv2_api" "cde_recommend" {
  name          = "cde-recommend-${var.environment}"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.cde_recommend.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.cde_recommend.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "post_recommend" {
  api_id    = aws_apigatewayv2_api.cde_recommend.id
  route_key = "POST /recommend"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.cde_recommend.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cde_recommend.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.cde_recommend.execution_arn}/*/*"
}
