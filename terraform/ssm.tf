resource "aws_ssm_parameter" "cloudflare_api_token" {
  name  = "/mc/cloudflare/api_token"
  type  = "SecureString"
  value = data.terraform_remote_state.tf_cloudflare.outputs.api_token_minecraft
}
