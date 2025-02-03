module "image_optimization_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 3.0"

  function_name = "image-optimization"
  handler       = "image_processing.lambda_handler"
  runtime       = "python3.9"
  memory_size   = 512
  timeout       = 10

  source_path = "./src/image-optimization"
  
  allowed_triggers = {
    cloudfront = {
      principal  = "cloudfront.amazonaws.com"
      source_arn = module.cloudfront.cloudfront_distribution_arn
    }
}

}