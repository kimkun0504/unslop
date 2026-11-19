variable "name" {
  description = "Globally unique bucket name."
  type        = string
  nullable    = false

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.name))
    error_message = "name must be 3 to 63 lowercase letters, digits or hyphens, starting and ending with a letter or digit."
  }
}

variable "noncurrent_version_days" {
  description = "Days to keep noncurrent object versions before deleting them."
  type        = number
  nullable    = false

  validation {
    condition     = var.noncurrent_version_days >= 1 && var.noncurrent_version_days <= 365 && floor(var.noncurrent_version_days) == var.noncurrent_version_days
    error_message = "noncurrent_version_days must be a whole number from 1 to 365."
  }
}
