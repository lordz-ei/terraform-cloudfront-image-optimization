variable "aws_region" {
  description = "The AWS region to deploy resources."
  default     = "us-east-1"
}

variable "create_origin_bucket" {
  description = "Create an S3 bucket for original images"
  type        = bool
  default     = false
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

variable "max_image_size" {
  description = "Maximum image size in bytes"
  type        = number
  default     = 4700000
}

variable "image_cache_ttl" {
  description = "TTL for transformed images in seconds"
  type        = string
  default     = "max-age=31622400"
}

variable "lambda_layer_arn" {
  description = "ARN of the Lambda layer" #used for adding the Pillow library layer
  type        = string
}
