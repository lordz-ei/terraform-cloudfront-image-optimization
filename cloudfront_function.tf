resource "aws_cloudfront_function" "cloudfront_url_rewrite" {
  name    = "cloudfront-url-rewrite"
  runtime = "cloudfront-js-1.0"
  publish = true
  code    = file("./src/url-rewrite/index.js")
}
