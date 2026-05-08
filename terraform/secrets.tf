resource "aws_secretsmanager_secret" "anthropic" {
  name        = "${var.project_name}/anthropic-api-key"
  description = "Anthropic API key for the Lambda agent."
  tags        = local.tags
}

# Create the secret with a placeholder. The real value is set manually via CLI:
#   aws secretsmanager put-secret-value \
#     --secret-id <name> --secret-string "sk-ant-..."
# ignore_changes keeps Terraform from overwriting it on subsequent applies.
resource "aws_secretsmanager_secret_version" "anthropic" {
  secret_id     = aws_secretsmanager_secret.anthropic.id
  secret_string = "placeholder"

  lifecycle {
    ignore_changes = [secret_string]
  }
}
