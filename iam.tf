#Create IAM Role for Lambda
module "lambda_iam_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-assumable-role"
  version = "~> 5.0"

  create_role = true
  role_name   = "lambda-image-optimizer-role"

  trusted_role_services = ["lambda.amazonaws.com"]
}

