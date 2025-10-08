terraform {
  required_version = "~> 1.10"

  backend "s3" {
    bucket       = "mdekort.tfstate"
    key          = "tf-minecraft.tfstate"
    region       = "eu-west-1"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

provider "cloudflare" {
  api_token = data.terraform_remote_state.tf_cloudflare.outputs.api_token_minecraft
}
