build_legacy() {
  cat > main.tf <<'TF'
# legacy
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

variable "name" {}

resource "aws_s3_bucket" "logs" {
  bucket = var.name
}
TF
  printf '.terraform/\n' > .gitignore
}
cases() {
  printf 'variable "region" {\n  type = string # where\n}\n' > region.tf
  expect_fail "comment" "comments are forbidden"
  printf 'variable "stage" {}\n' > stage.tf
  expect_fail "untyped variable" "terraform_typed_variables"
  printf 'variable "zone" {\ntype=string\n}\n' > zone.tf
  expect_fail "unformatted new file" "new file is not formatted"
  printf 'resource "aws_s3_bucket" "data" {\n  bucket = "legacy-data"\n}\n' > data.tf
  expect_fail "new insecure bucket" "CKV"
  printf 'variable "owner" {\n  type        = string\n  description = "Team that owns the bucket."\n}\n' > owner.tf
  expect_pass "clean new variable"
}
