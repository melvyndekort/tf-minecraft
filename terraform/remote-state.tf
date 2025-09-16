data "terraform_remote_state" "tf_cloudflare" {
  backend = "s3"

  config = {
    bucket = "mdekort.tfstate"
    key    = "tf-cloudflare.tfstate"
    region = "eu-west-1"
  }
}
