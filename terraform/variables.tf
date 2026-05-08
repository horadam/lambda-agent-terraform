variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region for all resources."
}

variable "project_name" {
  type        = string
  default     = "lambda-agent"
  description = "Prefix applied to every resource name."
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Deployment environment (dev / staging / prod)."
}

variable "owner" {
  type        = string
  default     = ""
  description = "Team or individual responsible for this stack (shows in Cost Explorer)."
}
