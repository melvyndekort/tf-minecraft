# Bootstrap Infrastructure

This directory contains the minimal Terraform configuration to create the GitHub Actions OIDC role.

## Usage

```bash
cd bootstrap
terraform init
terraform apply
```

Copy the output role ARN to your GitHub repository secrets as `AWS_ROLE_ARN`.

## Why Separate?

The OIDC role cannot be in the main Terraform codebase because:
- The role is needed to deploy the main infrastructure
- Circular dependency: main code needs role, role deploys main code
- Bootstrap runs once manually, main pipeline runs automatically