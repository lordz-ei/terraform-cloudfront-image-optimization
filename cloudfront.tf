module "cloudfront" {
  source  = "terraform-aws-modules/cloudfront/aws"
  version = "~> 2.0"

  comment = "Image Optimization CloudFront with Failover"

  origin = {
    transformed_s3 = {
      domain_name = module.transformed_s3_bucket.s3_bucket_bucket_domain_name
      origin_id   = "TransformedS3Bucket"
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
      event_type   = "viewer-request"
      function_arn = module.cloudfront_url_rewrite.cloudfront_function_arn
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
