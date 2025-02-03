module "image_optimization_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 3.0"

  function_name = "image-optimization"
  handler       = "image_processing.lambda_handler"
  runtime       = "python3.9"
  memory_size   = 512
  timeout       = 10

  source_path = "./src/image-optimization"
  
  create_lambda_function_url = true
  authorization_type         = "AWS_IAM"

  environment_variables = {
    S3_ORIGINAL_IMAGE_BUCKET = module.original_s3_bucket.s3_bucket_id
    S3_TRANSFORMED_IMAGE_BUCKET = module.transformed_s3_bucket.s3_bucket_id
  }
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudFront"
  action        = "lambda:InvokeFunctionUrl"
  function_name = module.image_optimization_lambda.lambda_function_name
  principal     = "cloudfront.amazonaws.com"
  source_arn    = module.cloudfront.cloudfront_distribution_arn

  depends_on = [ module.cloudfront ]
}