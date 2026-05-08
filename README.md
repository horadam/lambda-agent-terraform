# Lambda Agent on AWS

A simple AI agent (Claude) running as an AWS Lambda function, deployed via Terraform and GitHub Actions with OIDC auth.

## Milestones

- [x] Milestone 1 — Local Lambda function + agent code
- [x] Milestone 2 — Terraform: deploy Lambda from laptop
- [ ] Milestone 3 — Secrets Manager for API key
- [x] Milestone 4 — GitHub Actions deploys via OIDC

## Local development

### Install dependencies

```bash
pip install -r agent/requirements.txt
```

### Run tests

```bash
python3 -m pytest agent/tests/ -v
```

### Invoke the handler locally

```bash
ANTHROPIC_API_KEY=sk-ant-... python3 -c \
  "from agent.handler import handler; print(handler({'body': '{\"input\": \"what time is it?\"}'}, None))"
```

## Deploy to AWS (Milestone 2+)

Prerequisites: Terraform ≥ 1.9, AWS CLI configured (`aws configure`).

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

`terraform apply` will:
1. pip-install deps into `lambda_package/` and zip it as `agent.zip`
2. Create the Lambda execution IAM role
3. Create the CloudWatch log group (14-day retention)
4. Deploy the Lambda function
5. Attach a Function URL

The Lambda will fail with a missing API key error until Milestone 3.
