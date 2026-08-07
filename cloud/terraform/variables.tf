variable "aws_region" {
  description = "AWS region for the deployment."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Base project name used for AWS resources."
  type        = string
  default     = "ai-data-augmentor"
}

variable "table_name" {
  description = "DynamoDB table name."
  type        = string
  default     = "ai-data-augmentor-companies"
}
