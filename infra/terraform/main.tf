terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
}

resource "cloudflare_worker_script" "visamate_worker" {
  name    = "automatters-api"
  content = file("${path.module}/../../compose/edge-worker/index.js")
}

resource "cloudflare_queue" "document_queue" {
  name = "document-processing"
}

resource "cloudflare_kv_namespace" "cache" {
  title = "visamate-cache"
}