# IAM role for the ingest Lambda
data "aws_iam_policy_document" "ingest_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ingest" {
  name               = "${var.project_prefix}-ingest-role"
  assume_role_policy = data.aws_iam_policy_document.ingest_assume.json
}

# Policy: PutItem to DynamoDB and read object from S3; write logs
data "aws_iam_policy_document" "ingest_policy" {
  statement {
    actions = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.photos.arn]
  }
  statement {
    actions = ["s3:GetObject", "s3:GetObjectTagging"]
    resources = ["${aws_s3_bucket.uploads.arn}/*"]
  }
  statement {
    actions = ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "ingest_policy" {
  name   = "${var.project_prefix}-ingest-policy"
  policy = data.aws_iam_policy_document.ingest_policy.json
}

resource "aws_iam_role_policy_attachment" "ingest_attach" {
  role       = aws_iam_role.ingest.name
  policy_arn = aws_iam_policy.ingest_policy.arn
}

# Ingest Lambda (EXIF extraction)
resource "aws_lambda_function" "ingest" {
  function_name = "${var.project_prefix}-ingest"
  role          = aws_iam_role.ingest.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  filename      = var.ingest_zip_path
  timeout       = 30
  memory_size   = 256
  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.photos.name
    }
  }
}

# Allow S3 to invoke Lambda
resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.uploads.arn
}
