variable "aws_region" {
  description = "The AWS region to deploy resources."
  default     = "us-east-1"
}

variable "original_image_bucket_name" {
  description = "Name of the original image bucket"
  type        = string
}

variable "transformed_image_bucket_name" {
  description = "Name of the transformed image bucket"
  type        = string
}

variable "cloudfront_log_bucket_name" {
  description = "S3 bucket for CloudFront logs"
  type        = string
}

variable "min_ttl" {
  description = "Minimum TTL for CloudFront cache"
  type        = number
  default     = 86400
}

variable "default_ttl" {
  description = "Default TTL for CloudFront cache"
  type        = number
  default     = 604800
}

variable "max_ttl" {
  description = "Maximum TTL for CloudFront cache"
  type        = number
  default     = 2592000
}