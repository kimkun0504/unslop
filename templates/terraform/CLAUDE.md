# Project

Terraform 1.17 on AWS. The root module in this folder composes reusable modules from `modules/`; each module owns one concern and exposes typed, validated variables. State lives in an S3 backend with native locking.

- `scripts/setup` checks the pinned toolchain, initialises providers and tflint plugins.
- `scripts/fast-check` must pass before you stop: no comments, suppressions, fmt, validate, tflint (all rules plus AWS), `terraform test` with mocked providers.
- `scripts/verify` is what CI runs: fast-check plus checkov security scanning.

Validate every input variable. Encrypt, version and block public access by default, as `modules/storage_bucket` does. Test each module with `command = plan` and a mocked provider; test every validation with `expect_failures`.

You may run `terraform plan`. You never run `apply`, `destroy`, `import` or `state` commands; those happen in a reviewed pipeline. You cannot edit `versions.tf`, `.tflint.hcl`, `.checkov.yaml` or the lockfile.
