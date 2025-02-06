# Web Performance and Image Optimization using AWS CloudFrond, Lambda, S3

Images typically constitute the largest components of web pages, consuming significant bandwidth and generating multiple HTTP requests. Effective image optimization is crucial for several reasons: it enhances user experience, reduces content delivery costs, and improves search engine rankings. A prime example is Google's Largest Contentful Paint metric, which heavily weights image optimization in its search ranking calculations.

Our Solution Architecture

We've developed an efficient, serverless approach to image optimization that leverages three key AWS services: Amazon CloudFront, Amazon S3, and AWS Lambda. This architecture provides a streamlined solution that handles most common image optimization needs.

The system processes images centrally within an AWS Region, performing transformations only when necessary - that is, when a specific variant hasn't been previously generated and cached. The solution supports two primary transformation types:
- Image resizing
- Format conversion

Both transformations can be requested directly from the frontend application. Additionally, the system can automatically select the optimal image format based on server-side analysis.

Core Components:
- Amazon S3 handles image storage
- Amazon CloudFront manages content delivery
- AWS Lambda performs image processing

This serverless architecture ensures efficient resource usage while maintaining high performance and scalability. The system processes each image request through a well-defined flow, which is illustrated in the following diagram.

![The proposed solution architecture](architecture.png)

## Overview

This Terraform module helps you quickly set up an AWS CloudFront distribution with settings optimized for image delivery. It allows for configuring the origin domain, caching policies, and other settings required to efficiently serve images. Whether you’re building a web application or a content delivery solution, this module can help reduce your image load times and improve overall performance.

## Features

- **Customizable Origin:** Easily configure your origin domain from which images are served.
- **Optimized Caching:** Leverage CloudFront caching mechanisms to optimize image delivery.
- **Flexible Configuration:** Supports additional settings for SSL, error handling, and more.
- **Easy Integration:** Designed to be integrated seamlessly with other Terraform-managed AWS resources.

## Prerequisites

- **Terraform:** Version 0.12 or later.
- **AWS Provider:** Ensure you have configured the AWS provider with the necessary credentials and permissions.
- **AWS Account:** An active AWS account with permissions to create CloudFront distributions.

## Usage

To use this module, include it in your Terraform configuration as follows:

```hcl
module "cloudfront_image_optimization" {
  source             = "github.com/lordz-ei/terraform-cloudfront-image-optimization"
  
  # Required variables
  original_image_bucket_name = "your-image-origin-s3-bucket"
  transformed_image_bucket_name = "your-transformed-image-s3-bucket"
  cloudfront_log_bucket_name = "your-cloudfront-logs-s3-bucket"

  #(Optional) CloudFront ttl variables based on your configuration needs.
  min_ttl = 0 #Minimum TTL for CloudFront cache, default 86400
  default_ttl = 3600 #Default TTL for CloudFront cache, default 604800
  max_ttl = 7200 #Maximum TTL for CloudFront cache, default 2592000
  
  #(Optional) Maximum image size in bytes
  max_image_size = 1024 #Default set to 4700000

  #(Optional)TTL for transformed images in seconds
  image_cache_ttl = "max-age=96000" #Default set to "max-age=31622400"
}
