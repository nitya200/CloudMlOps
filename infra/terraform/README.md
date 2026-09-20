# Terraform module

See [../README.md](../README.md) for bootstrap order.

After `terraform apply`, run:

```bash
terraform output backend_service_url
terraform output github_secrets_checklist
```

Update backend `CORS_ORIGINS` to the frontend App Runner URL after the first apply.
