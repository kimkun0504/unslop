mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
    }
  }
}

variables {
  name                    = "acme-dev-artifacts"
  noncurrent_version_days = 30
}

run "applies_secure_defaults" {
  command = plan

  module {
    source = "./modules/storage_bucket"
  }

  assert {
    condition     = aws_s3_bucket_versioning.this.versioning_configuration[0].status == "Enabled"
    error_message = "versioning must be enabled"
  }

  assert {
    condition = alltrue([
      aws_s3_bucket_public_access_block.this.block_public_acls,
      aws_s3_bucket_public_access_block.this.block_public_policy,
      aws_s3_bucket_public_access_block.this.ignore_public_acls,
      aws_s3_bucket_public_access_block.this.restrict_public_buckets,
    ])
    error_message = "all public access must be blocked"
  }

  assert {
    condition     = one(aws_s3_bucket_ownership_controls.this.rule).object_ownership == "BucketOwnerEnforced"
    error_message = "ACLs must be disabled through BucketOwnerEnforced"
  }

  assert {
    condition     = one(one(aws_s3_bucket_server_side_encryption_configuration.this.rule).apply_server_side_encryption_by_default).sse_algorithm == "aws:kms"
    error_message = "objects must be encrypted with KMS"
  }

  assert {
    condition     = aws_kms_key.this.enable_key_rotation
    error_message = "the KMS key must rotate"
  }

  assert {
    condition     = aws_s3_bucket_lifecycle_configuration.this.rule[0].noncurrent_version_expiration[0].noncurrent_days == 30
    error_message = "noncurrent versions must expire after the configured days"
  }
}

run "rejects_invalid_bucket_names" {
  command = plan

  module {
    source = "./modules/storage_bucket"
  }

  variables {
    name = "Not_Valid"
  }

  expect_failures = [var.name]
}

run "rejects_fractional_retention" {
  command = plan

  module {
    source = "./modules/storage_bucket"
  }

  variables {
    noncurrent_version_days = 1.5
  }

  expect_failures = [var.noncurrent_version_days]
}

run "rejects_unbounded_retention" {
  command = plan

  module {
    source = "./modules/storage_bucket"
  }

  variables {
    noncurrent_version_days = 366
  }

  expect_failures = [var.noncurrent_version_days]
}
