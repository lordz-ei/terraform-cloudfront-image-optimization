resource "aws_cloudfront_cache_policy" "image_optimization_cache_policy" {
  name        = "image-optimization-cache-policy"
  comment     = "Cache policy for image optimization"
  default_ttl = var.default_ttl
  min_ttl     = var.min_ttl
  max_ttl     = var.max_ttl
  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "none"
    }
    query_strings_config {
      query_string_behavior = "none"
    }
  }
}

resource "aws_cloudfront_response_headers_policy" "image_optimization_response_header_policy" {
  name    = "image-optimization-response-header-policy"
  comment = "Response header policy for image optimization"

  cors_config {
    access_control_allow_credentials = false

    access_control_allow_headers {
      items = ["*"]
    }

    access_control_allow_methods {
      items = ["GET"]
    }

    access_control_allow_origins {
      items = ["*"]
    }
    access_control_expose_headers {
      items = ["-"]
    }

    access_control_max_age_sec = 600
    origin_override            = true
  }

  custom_headers_config {
    items {
      header   = "x-aws-image-optimization"
      override = true
      value    = "v1.0"
    }

    items {
      header   = "vary"
      override = true
      value    = "accept"
    }
  }
}

module "cloudfront" {
  source  = "terraform-aws-modules/cloudfront/aws"
  version = "~> 4.0"

  comment = "Image Optimization CloudFront with Failover"

  create_origin_access_control = true
  origin_access_control = {
    s3_oac = {
      description      = "CloudFront access to S3"
      origin_type      = "s3"
      signing_behavior = "always"
      signing_protocol = "sigv4"
    }

    lambda_oac = {
      description      = "CloudFront access to Lambda"
      origin_type      = "lambda"
      signing_behavior = "always"
      signing_protocol = "sigv4"
    }
  }

  origin = {
    s3 = {
      domain_name           = module.transformed_s3_bucket.s3_bucket_bucket_regional_domain_name
      origin_access_control = "s3_oac"
      origin_shield = {
        enabled              = true
        origin_shield_region = var.aws_region
      }
    }

    lambda = {
      domain_name           = "${module.image_optimization_lambda.lambda_function_url_id}.lambda-url.${data.aws_region.current.name}.on.aws"
      origin_access_control = "lambda_oac"
      custom_origin_config = {
        http_port              = 80
        https_port             = 443
        origin_protocol_policy = "https-only"
        origin_ssl_protocols   = ["TLSv1.2"]
      }
      origin_shield = {
        enabled              = true
        origin_shield_region = var.aws_region
      }
    }
  }

  origin_group = {
    lambda_failover = {
      failover_status_codes      = [403, 404, 500, 502]
      primary_member_origin_id   = "s3"
      secondary_member_origin_id = "lambda"
    }
  }

  default_cache_behavior = {
    target_origin_id       = "lambda_failover"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]

    use_forwarded_values       = false
    cache_policy_id            = aws_cloudfront_cache_policy.image_optimization_cache_policy.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.image_optimization_response_header_policy.id

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

  web_acl_id = var.create_waf ? element(aws_wafv2_web_acl.cloudfront_acl[*].id, 0) : null

  depends_on = [module.image_optimization_lambda]
}
