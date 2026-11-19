module "artifacts" {
  source = "./modules/storage_bucket"

  name                    = "${var.project}-${var.environment}-artifacts"
  noncurrent_version_days = var.environment == "prod" ? 90 : 30
}
