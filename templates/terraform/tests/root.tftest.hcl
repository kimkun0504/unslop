mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
    }
  }
}

variables {
  project     = "acme"
  environment = "dev"
}

run "plans_with_valid_inputs" {
  command = plan
}

run "rejects_unknown_environments" {
  command = plan

  variables {
    environment = "qa"
  }

  expect_failures = [var.environment]
}

run "rejects_invalid_project_names" {
  command = plan

  variables {
    project = "Acme"
  }

  expect_failures = [var.project]
}
