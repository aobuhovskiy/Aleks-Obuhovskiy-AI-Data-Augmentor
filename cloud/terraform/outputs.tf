output "dynamodb_table_name" {
  description = "DynamoDB table that stores enriched company records."
  value       = aws_dynamodb_table.companies.name
}

output "lambda_function_name" {
  description = "Serverless Lambda function used to retrieve company data."
  value       = aws_lambda_function.company_api.function_name
}

output "aws_region" {
  description = "Deployment region."
  value       = var.aws_region
}
