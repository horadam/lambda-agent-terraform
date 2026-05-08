output "function_url" {
  description = "HTTPS endpoint to invoke the agent."
  value       = aws_lambda_function_url.agent.function_url
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role."
  value       = aws_iam_role.lambda.arn
}
