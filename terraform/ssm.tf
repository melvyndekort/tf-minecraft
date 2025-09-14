resource "aws_ssm_parameter" "cloudflare_api_token" {
  name  = "/mc/cloudflare/api_token"
  type  = "SecureString"
  value = local.secrets.cloudflare.api_token
}
