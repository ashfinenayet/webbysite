# Role
data "aws_iam_policy_document" "query_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals { type = "Service", identifiers = ["lambda.amazonaws.com"] }
  }
}
resource "aws_iam_role" "query" {
  name               = "${var.project_prefix}-query-role"
  assume_role_policy = data.aws_iam_policy_document.query_assume.json
}

data "aws_iam_policy_document" "query_policy" {
  statement {
    actions  = ["dynamodb:GetItem","dynamodb:Query","dynamodb:Scan"]
    resources = [aws_dynamodb_table.photos.arn]
  }
  statement {
    actions   = ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"]
    resources = ["*"]
  }
}
resource "aws_iam_policy" "query_policy" {
  name   = "${var.project_prefix}-query-policy"
  policy = data.aws_iam_policy_document.query_policy.json
}
resource "aws_iam_role_policy_attachment" "query_attach" {
  role       = aws_iam_role.query.name
  policy_arn = aws_iam_policy.query_policy.arn
}

resource "aws_lambda_function" "query" {
  function_name = "${var.project_prefix}-query"
  role          = aws_iam_role.query.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  filename      = var.query_zip_path
  timeout       = 15
  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.photos.name
    }
  }
}

# HTTP API
resource "aws_apigatewayv2_api" "http_api" {
  name          = "${var.project_prefix}-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.query.arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /metadata"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_lambda_permission" "allow_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

output "api_url" {
  value = aws_apigatewayv2_api.http_api.api_endpoint
}
