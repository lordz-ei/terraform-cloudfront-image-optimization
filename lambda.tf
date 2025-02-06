module "image_optimization_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 3.0"

  function_name = "image-optimization"
  handler       = "image_processing.handler"
  runtime       = "python3.9"
  memory_size   = 512
  timeout       = 10

  source_path = "./src/image-optimization"

  create_lambda_function_url = true
  attach_policy_json         = true
  authorization_type         = "AWS_IAM"

  layers = [
    var.lambda_layer_arn
  ]

  policy_json = data.aws_iam_policy_document.lambda_policy_document.json

  environment_variables = {
    originalImageBucketName    = var.original_image_bucket_name
    transformedImageBucketName = module.transformed_s3_bucket.s3_bucket_id
    maxImageSize               = var.max_image_size
    transformedImageCacheTTL   = var.image_cache_ttl
  }
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudFront"
  action        = "lambda:InvokeFunctionUrl"
  function_name = module.image_optimization_lambda.lambda_function_name
  principal     = "cloudfront.amazonaws.com"
  source_arn    = module.cloudfront.cloudfront_distribution_arn

  depends_on = [module.cloudfront]
}
