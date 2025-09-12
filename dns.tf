locals {
  fqdn = "${var.dns_record}.${var.dns_zone}"
}

data "cloudflare_zone" "zone" {
  filter = {
    name = var.dns_zone
  }
}

resource "cloudflare_dns_record" "mc_a" {
  zone_id = data.cloudflare_zone.zone.zone_id
  name    = local.fqdn
  type    = "A"
  content = "1.1.1.1"
  ttl     = 120
  proxied = false

  lifecycle {
    ignore_changes = [content]
  }
}

resource "cloudflare_dns_record" "mc_aaaa" {
  zone_id = data.cloudflare_zone.zone.zone_id
  name    = local.fqdn
  type    = "AAAA"
  content = "2001:db8::1"
  ttl     = 120
  proxied = false

  lifecycle {
    ignore_changes = [content]
  }
}
