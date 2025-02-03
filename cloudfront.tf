module "cloudfront" {
  source  = "terraform-aws-modules/cloudfront/aws"
  version = "~> 2.0"

  comment = "Image Optimization CloudFront with Failover"

  create_origin_access_identity = true

  origin_access_identities = {
    transformed_s3_bucket = "TransformedS3Bucket"
  }
  
  origin = {
    transformed_s3 = {
      domain_name = module.transformed_s3_bucket.s3_bucket_bucket_domain_name
      origin_id   = "transformed_s3_bucket"

      s3_origin_config = {
        origin_access_identity = module.cloudfront_oac.cloudfront_origin_access_identity_path
      }
    }

    lambda_failover = {
      domain_name = module.image_optimization_lambda.lambda_function_invoke_arn
      origin_id   = "LambdaFailover"

      custom_origin_config = {
        http_port  = 80
        https_port = 443
        origin_protocol_policy = "https-only"
      }
    }
  }

  default_cache_behavior = {
    target_origin_id       = "TransformedS3Bucket"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]

    forwarded_values = {
      query_string = true
      headers      = ["Accept"]
    }

    min_ttl     = var.min_ttl
    default_ttl = var.default_ttl
    max_ttl     = var.max_ttl

    function_association = {
        # Valid keys: viewer-request, viewer-response
        viewer-request = {
          function_arn = aws_cloudfront_function.cloudfront_url_rewrite.arn
        }
    }

  logging_config = {
    include_cookies = false
    bucket          = module.cloudfront_logs.s3_bucket_bucket_domain_name
    prefix          = "cloudfront-logs/"
  }


    geo_restriction = {
      restriction_type = "none"
    }
  

  viewer_certificate = {
    cloudfront_default_certificate = true
  }
}
}