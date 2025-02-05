#Create IAM Role for Lambda
module "lambda_iam_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-assumable-role"
  version = "~> 5.0"

  create_role = true
  role_name   = "lambda-image-optimizer-role"

  trusted_role_services = ["lambda.amazonaws.com"]
}

data "aws_iam_policy_document" "lambda_policy_document" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
      "s3:DeleteObject"
    ]

    resources = [
      module.transformed_s3_bucket.s3_bucket_arn,
      module.original_s3_bucket.s3_bucket_arn,
      "${module.transformed_s3_bucket.s3_bucket_arn}/*",
      "${module.original_s3_bucket.s3_bucket_arn}/*"
    ]
  }
}
