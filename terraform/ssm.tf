resource "aws_ssm_parameter" "cloudflare_api_token" {
  name  = "/mc/cloudflare/api_token"
  type  = "SecureString"
  value = data.terraform_remote_state.tf_cloudflare.outputs.api_token_minecraft
}

resource "aws_ssm_parameter" "discord_webhook_url" {
  name  = "/mc/discord/webhook_url"
  type  = "SecureString"
  value = local.secrets.discord.webhook_url
}
