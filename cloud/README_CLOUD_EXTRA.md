# Extra Challenge: AWS Serverless + NoSQL + Terraform

This folder extends the AI Data Augmentor into a small serverless AWS architecture.

## What This Demonstrates

- **Infrastructure as Code:** Terraform
- **Serverless Compute:** AWS Lambda
- **NoSQL Database:** Amazon DynamoDB
- **Scalability:** Lambda and DynamoDB scale without managing application servers

## Architecture

```text
Final validated Excel
        |
        v
src/upload_to_dynamodb.py
        |
        v
Amazon DynamoDB
        |
        v
AWS Lambda
   |         |
   v         v
List all    Get one
companies   company
```

The data-enrichment crawler remains separate from the cloud serving layer. This keeps the cloud component small, explainable, and inexpensive.

## Files

```text
lambda/
  lambda_function.py

src/
  upload_to_dynamodb.py

terraform/
  main.tf
  variables.tf
  outputs.tf
  terraform.tfvars.example

tests/
  test_lambda_local.py
```

## Lambda Actions

Health check:

```json
{
  "action": "health"
}
```

List companies:

```json
{
  "action": "list"
}
```

Get one company:

```json
{
  "action": "get",
  "company_name": "Patagonia"
}
```

## Local Validation

From the cloud-extra folder:

```bash
python tests/test_lambda_local.py
```

Expected result:

```text
PASS: Lambda local tests
```

## AWS Prerequisites

Before deployment you need:

1. An AWS account.
2. AWS CLI installed.
3. Terraform installed.
4. AWS credentials configured locally.

Verify AWS access:

```bash
aws sts get-caller-identity
```

Verify Terraform:

```bash
terraform version
```

## Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Terraform creates:

- DynamoDB table: `ai-data-augmentor-companies`
- Lambda function: `ai-data-augmentor-api`
- IAM role/policy for Lambda

The DynamoDB table uses `PAY_PER_REQUEST`, so there is no provisioned capacity to manage.

## Load the Final Dataset

Return to the repository root and run:

```bash
python cloud/src/upload_to_dynamodb.py \
  --file output/augmented-companies.xlsx \
  --table ai-data-augmentor-companies \
  --region us-east-1
```

On Windows PowerShell, use one line:

```powershell
python cloud/src/upload_to_dynamodb.py --file output/augmented-companies.xlsx --table ai-data-augmentor-companies --region us-east-1
```

## Test Lambda

Health:

```bash
aws lambda invoke \
  --function-name ai-data-augmentor-api \
  --payload '{"action":"health"}' \
  response.json
```

Get Patagonia:

```bash
aws lambda invoke \
  --function-name ai-data-augmentor-api \
  --payload '{"action":"get","company_name":"Patagonia"}' \
  response.json
```

List all companies:

```bash
aws lambda invoke \
  --function-name ai-data-augmentor-api \
  --payload '{"action":"list"}' \
  response.json
```

Depending on your AWS CLI configuration, you may need `--cli-binary-format raw-in-base64-out`.

## Destroy Resources

When the demonstration is finished:

```bash
cd terraform
terraform destroy
```

This removes the Terraform-managed Lambda, DynamoDB table, and IAM resources.

## Important Design Choice

The Lambda function is intentionally **not exposed publicly** through a Function URL or API Gateway. For this assignment, direct AWS invocation is enough to demonstrate serverless compute while avoiding an unnecessary public endpoint.
