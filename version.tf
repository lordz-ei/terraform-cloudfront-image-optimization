terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.54"
    }
  }

}

provider "aws" {
  region = var.aws_region
}