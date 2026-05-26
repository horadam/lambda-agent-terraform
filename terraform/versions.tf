terraform {
  required_version = ">= 1.9"

  backend "s3" {
    bucket         = "lambda-agent-tfstate-084375583552"
    key            = "lambda-agent/terraform.tfstate"
    region         = "us-east-1"
    use_lockfile   = true
    encrypt        = true
    profile        = "altimetrik-learning"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}
