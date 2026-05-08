# Build the deployment package by installing deps and copying source.
# The package preserves the agent/ subdirectory so handler.handler and
# "from agent.agent import run_agent" resolve the same way in Lambda as locally.
resource "null_resource" "build_package" {
  triggers = {
    requirements   = filemd5("${path.module}/../agent/requirements.txt")
    handler        = filemd5("${path.module}/../agent/handler.py")
    agent_code     = filemd5("${path.module}/../agent/agent.py")
    secrets        = filemd5("${path.module}/../agent/secrets.py")
    pip_invocation = "linux-wheels"
  }

  provisioner "local-exec" {
    command = <<-EOF
      set -e
      rm -rf ${path.module}/../lambda_package
      mkdir -p ${path.module}/../lambda_package/agent
      python3 -m pip install \
        -r ${path.module}/../agent/requirements.txt \
        -t ${path.module}/../lambda_package/ \
        --platform manylinux2014_x86_64 \
        --implementation cp \
        --python-version 3.12 \
        --only-binary=:all: \
        --upgrade -q
      cp ${path.module}/../agent/__init__.py ${path.module}/../lambda_package/agent/
      cp ${path.module}/../agent/agent.py    ${path.module}/../lambda_package/agent/
      cp ${path.module}/../agent/handler.py  ${path.module}/../lambda_package/agent/
      cp ${path.module}/../agent/secrets.py  ${path.module}/../lambda_package/agent/
    EOF
  }
}

data "archive_file" "agent_zip" {
  depends_on  = [null_resource.build_package]
  type        = "zip"
  source_dir  = "${path.module}/../lambda_package"
  output_path = "${path.module}/../agent.zip"
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}"
  retention_in_days = 14
  tags              = local.tags
}

resource "aws_lambda_function" "agent" {
  function_name    = var.project_name
  role             = aws_iam_role.lambda.arn
  handler          = "agent.handler.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.agent_zip.output_path
  source_code_hash = data.archive_file.agent_zip.output_base64sha256
  timeout     = 30
  memory_size = 128

  environment {
    variables = {
      SECRET_NAME = aws_secretsmanager_secret.anthropic.name
    }
  }

  # Explicit log group must exist before Lambda creates its own (with infinite retention).
  depends_on = [aws_cloudwatch_log_group.lambda]

  tags = local.tags
}

resource "aws_lambda_function_url" "agent" {
  function_name      = aws_lambda_function.agent.function_name
  authorization_type = "NONE"
}
