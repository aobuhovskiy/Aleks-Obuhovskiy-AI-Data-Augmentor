# AI Data Augmentor

## Overview

This project was created for **CAIO Assignment #3 – AI Data Augmentor**.

The goal was to take a starter spreadsheet of 50 outdoor and apparel companies and enrich the data with additional business information:

- Company location
- Customer service phone number
- Official website
- Source / verification information

The project demonstrates how AI-assisted automation can improve incomplete business data while also showing the importance of validation, source quality, confidence handling, and human review.

The final solution includes:

- Automated data augmentation
- Looping and retry logic
- Validation and human QA
- Streamlit user interface
- AWS serverless deployment
- DynamoDB NoSQL storage
- Terraform Infrastructure as Code
- GitHub Actions automated testing
- S3 + CloudFront CDN delivery

---

## Project Objectives

The main objectives were to:

1. Read the original company dataset.
2. Automatically research missing company information.
3. Validate results before saving them.
4. Retry unresolved fields using a controlled loop.
5. Avoid guessing when reliable information could not be found.
6. Store uncertain values as `UNKNOWN`.
7. Produce a clean augmented Excel spreadsheet.
8. Document the approach, challenges, and lessons learned.
9. Provide a simple UI for reviewing the data.
10. Extend the project with cloud, CI, NoSQL, serverless, and CDN technologies.

---

## Final Dataset

The final augmented dataset contains **50 companies**.

The output file is located at:

`output/augmented-companies.xlsx`

The main augmented fields are:

- `company_name`
- `Location`
- `Phone`
- `Website`
- `Source`

The final dataset was manually reviewed after the automated enrichment process.

When information could not be verified with reasonable confidence, the value was intentionally recorded as:

`UNKNOWN`

This was done to avoid introducing fabricated or unreliable information.

---

## Technology Stack

### Core Data Augmentation

- Python
- pandas
- openpyxl
- DDGS / DuckDuckGo Search
- requests
- BeautifulSoup
- phonenumbers
- JSON caching
- Visual Studio Code
- Git / GitHub

### User Interface

- Streamlit

### Cloud / Extra Challenge

- Terraform
- Amazon DynamoDB
- AWS Lambda
- AWS IAM
- AWS CLI
- boto3

### Super Extra Challenge

- Looping / retry logic
- GitHub Actions
- Amazon S3
- Amazon CloudFront CDN

---

## Project Structure

```text
Aleks-Obuhovskiy-AI-Data-Augmentor/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── app.py
├── README.md
├── requirements.txt
│
├── data/
│   ├── starter-companies.csv
│   └── ddgs_cache.json
│
├── output/
│   └── augmented-companies.xlsx
│
├── reflection/
│   └── Aleks_Obuhovskiy_AI_Data_Augmentor_Reflection.pdf
│
├── src/
│   ├── augment_companies.py
│   ├── augment_companies_LOOP_V1.py
│   ├── augment_companies_PRE_LOOP.py
│   └── augment_companies_Tavily.py
│
└── cloud/
    ├── README_CLOUD_EXTRA.md
    │
    ├── lambda/
    │   └── lambda_function.py
    │
    ├── src/
    │   └── upload_to_dynamodb.py
    │
    ├── terraform/
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   ├── cdn.tf
    │   ├── terraform.tfvars.example
    │   └── .terraform.lock.hcl
    │
    └── tests/
        └── test_lambda_local.py
```

---

# Data Augmentation Approach

## 1. Load the Starter Dataset

The Python augmentation script reads the original company list from:

`data/starter-companies.csv`

The starter dataset contains 50 outdoor and apparel-related companies.

## 2. Search for Missing Information

The application performs automated searches for company information.

The final implementation uses **DDGS / DuckDuckGo Search** as the main search mechanism.

The repository also contains an earlier Tavily-based version:

`src/augment_companies_Tavily.py`

This earlier version is kept to show the development process and how the solution changed after testing.

## 3. Prefer Official Sources

The enrichment process attempts to identify official company sources before accepting information.

The solution looks for:

- Official corporate websites
- Customer service pages
- Contact pages
- Company headquarters information
- Official support numbers

Results from retailers, unrelated businesses, regional sites, and suspicious look-alike domains are treated carefully.

## 4. Validate the Results

Automated search results are not accepted blindly.

Validation includes checks for:

- Incorrect or unrelated domains
- Regional domains instead of official corporate sites
- Retailer websites
- Look-alike domains
- Incorrect phone numbers
- International phone numbers when a U.S. customer-service number is expected
- Distribution centers confused with headquarters
- Incomplete or malformed addresses

## 5. Human Quality Assurance

Automated enrichment produced useful results, but several edge cases showed that search automation alone was not reliable enough.

A final human QA review was therefore performed using stronger official-source evidence.

When reliable information could not be confirmed, the result remained `UNKNOWN` rather than being guessed.

**Key lesson:** Automated enrichment can accelerate research, but high-quality business data still requires validation, confidence rules, and human review.

---

# Super Extra Challenge 1: Looping

The original one-pass enrichment workflow was extended with controlled looping.

Instead of trying only one search and stopping, unresolved fields can be retried using alternate search strategies.

The loop:

1. Searches for unresolved information.
2. Validates the result.
3. Stops immediately when a field is verified.
4. Tries another strategy when the field is still unresolved.
5. Stops after a limited number of attempts.
6. Leaves the result as `UNKNOWN` if verification still fails.

This avoids unlimited searching while demonstrating a more agent-like iterative workflow.

Example flow:

```text
Company
   |
   v
Search
   |
   v
Validate
   |
   +---- Verified ----> Save
   |
   v
Retry with alternate strategy
   |
   v
Retry limit reached?
   |
   +---- Yes ----> UNKNOWN
```

The official script is:

`src/augment_companies.py`

Backup and development versions are also preserved:

- `src/augment_companies_PRE_LOOP.py`
- `src/augment_companies_LOOP_V1.py`

---

# Running the Data Augmentor

Install the required Python packages:

```bash
python -m pip install -r requirements.txt
```

Run the augmentation process:

```bash
python src/augment_companies.py
```

The resulting spreadsheet is written to:

`output/augmented-companies.xlsx`

---

# Streamlit UI Challenge

A Streamlit interface was added as an optional challenge.

Run it with:

```bash
python -m streamlit run app.py
```

The interface includes:

- Final Dataset
- Try the Agent
- How It Works

The Streamlit interface provides a simple business-facing way to demonstrate the solution without requiring the evaluator to work directly with the Python scripts.

---

# Extra Challenge: AWS Serverless Deployment

The project was extended with a cloud architecture using **Terraform, Amazon DynamoDB, and AWS Lambda**.

This satisfies the optional extra challenge requirements for:

- Infrastructure as Code
- NoSQL database
- Serverless compute

## Cloud Architecture

```text
Validated Excel Dataset
        |
        v
upload_to_dynamodb.py
        |
        v
Amazon DynamoDB
        |
        v
AWS Lambda
```

## Terraform – Infrastructure as Code

Terraform is used to provision and manage the AWS infrastructure.

Terraform configuration is located in:

`cloud/terraform/`

The deployment process included:

```bash
terraform init
terraform validate
terraform plan
terraform apply
```

Terraform successfully created and managed the required AWS resources.

## Amazon DynamoDB – NoSQL Database

Amazon DynamoDB is used as the NoSQL database.

Table name:

`ai-data-augmentor-companies`

The validated Excel dataset was uploaded using:

`cloud/src/upload_to_dynamodb.py`

A total of **50 company records** were successfully uploaded to DynamoDB.

## AWS Lambda – Serverless Compute

AWS Lambda provides the serverless compute layer.

Lambda function:

`ai-data-augmentor-api`

The Lambda supports operations such as:

### Health Check

```json
{
  "action": "health"
}
```

### List Companies

```json
{
  "action": "list"
}
```

### Retrieve a Company

```json
{
  "action": "get",
  "company_name": "Patagonia"
}
```

---

# Cloud Validation

The deployed Lambda function was successfully tested against the real DynamoDB table.

## Health Test

The Lambda health check returned:

```json
{
  "statusCode": 200
}
```

The response confirmed that the service was operational and connected to:

`ai-data-augmentor-companies`

## Real Company Retrieval Test

A second test requested:

```json
{
  "action": "get",
  "company_name": "Patagonia"
}
```

The Lambda successfully retrieved the Patagonia record from DynamoDB, including:

- Official website
- Ventura, California location
- Customer-service phone number
- Verification/source information

This demonstrated the complete cloud flow:

```text
Validated Dataset
        ↓
    DynamoDB
        ↓
     Lambda
        ↓
Company Record Returned
```

---

# Local Lambda Testing

Before deploying to AWS, the Lambda logic was tested locally.

Run:

```bash
python cloud/tests/test_lambda_local.py
```

Successful result:

```text
PASS: Lambda local tests
```

---

# Super Extra Challenge 2: GitHub Actions

A GitHub Actions workflow was added at:

`.github/workflows/ci.yml`

The workflow runs automatically on pushes and pull requests to the `main` branch.

It performs:

### Python Checks

- Checks out the repository
- Installs Python 3.12
- Installs project dependencies
- Checks Python syntax
- Runs the local Lambda test

### Terraform Checks

- Installs Terraform
- Runs `terraform init`
- Runs `terraform validate`

Both workflow jobs were successfully executed in GitHub Actions with green status.

Current workflow behavior is intentionally focused on **CI validation**. AWS deployment remains manual so infrastructure is not modified automatically by every GitHub push.

---

# Super Extra Challenge 3: S3 + CloudFront CDN

The final Excel output was also published through an AWS Content Delivery Network.

The CDN infrastructure is defined in:

`cloud/terraform/cdn.tf`

Terraform provisions:

- Private Amazon S3 bucket
- S3 public-access protection
- CloudFront Origin Access Control
- CloudFront distribution
- S3 bucket policy allowing CloudFront read access

The S3 bucket remains private. CloudFront is used to deliver the file securely.

## CDN Architecture

```text
augmented-companies.xlsx
        |
        v
Amazon S3
   private bucket
        |
        v
Amazon CloudFront
        |
        v
CDN Download URL
```

The final workbook was uploaded to S3 and successfully downloaded through CloudFront.

CDN URL:

https://d2uhh4vke00btl.cloudfront.net/augmented-companies.xlsx

This completed the CDN portion of the Super Extra Challenge.

---

# Final End-to-End Architecture

```text
Starter CSV
    |
    v
Python Data Augmentor
    |
    +--> Search
    +--> Validate
    +--> Loop / Retry
    +--> Human QA
    |
    v
Validated Excel
    |
    +--------------------+
    |                    |
    v                    v
Streamlit UI          DynamoDB
                         |
                         v
                      Lambda

Validated Excel
    |
    v
Private S3 Bucket
    |
    v
CloudFront CDN

GitHub Push
    |
    v
GitHub Actions
    |
    +--> Python Checks
    +--> Lambda Test
    +--> Terraform Validation
```

---

# Data Quality and Hallucination Control

A major focus of this project was preventing incorrect information from appearing authoritative.

The following rules were used:

1. Prefer official company sources.
2. Reject unrelated or suspicious domains.
3. Validate extracted phone numbers.
4. Review questionable locations manually.
5. Preserve source information when possible.
6. Retry unresolved fields using controlled looping.
7. Use `UNKNOWN` when confidence is insufficient.
8. Perform human QA before considering the spreadsheet final.

The project intentionally prioritizes **data reliability over completeness**.

---

# Challenges and Lessons Learned

The most difficult part of this project was not generating information. It was determining whether the information was trustworthy.

Automated search frequently returned plausible-looking but incorrect results.

Examples included:

- Regional company websites
- Retail websites
- Similar business names
- Incorrect customer-service numbers
- International numbers
- Distribution-office addresses
- Outdated company information

These issues demonstrated that a data augmentation agent needs more than search capability.

It also needs:

- Source prioritization
- Validation rules
- Confidence handling
- Looping and retry control
- Exception management
- Human review for ambiguous cases

The project also demonstrated how a local AI-assisted workflow can be expanded into a cloud architecture with automated validation and CDN delivery.

---

# Assignment Deliverables

## Required Deliverables

- Augmented company spreadsheet
- Python augmentation workflow
- GitHub repository
- One-page reflection PDF

## Challenge Deliverables

- README documentation
- Streamlit user interface

## Extra Challenge Deliverables

- Terraform Infrastructure as Code
- Amazon DynamoDB NoSQL database
- AWS Lambda serverless compute
- Local Lambda validation
- Real AWS deployment
- Live DynamoDB company retrieval through Lambda

## Super Extra Challenge Deliverables

- Looping / iterative retry process
- GitHub Actions automated CI workflow
- Successful Python and Terraform checks in GitHub Actions
- Amazon S3 output storage
- Amazon CloudFront CDN
- Successful download of the final Excel file through the CDN

---

# Reflection

The one-page project reflection is located at:

`reflection/Aleks_Obuhovskiy_AI_Data_Augmentor_Reflection.pdf`

It summarizes:

- Objective
- Tool stack
- Execution strategy
- Challenges
- Quality control
- Lessons learned

---

# Key Takeaway

The project started as a spreadsheet enrichment exercise and evolved into a broader AI-assisted data and cloud workflow.

```text
Search
  ↓
Validation
  ↓
Loop / Retry
  ↓
Human QA
  ↓
Excel Dataset
  ↓
Streamlit UI
  ↓
DynamoDB
  ↓
AWS Lambda

Excel Dataset
  ↓
Amazon S3
  ↓
CloudFront CDN

GitHub Push
  ↓
GitHub Actions
  ↓
Automated Validation
```

The most important lesson was that successful AI automation is not only about generating results. It is also about creating controls that determine when the system should trust a result, retry it, reject it, or clearly return `UNKNOWN`.

---

## Author

**Aleks Obuhovskiy**

CAIO Assignment #3 – AI Data Augmentor

## Live Streamlit App

The AI Data Augmentor UI is deployed and publicly accessible through Streamlit Community Cloud:

[Open the AI Data Augmentor UI](https://aleks-obuhovskiy-ai-data-augmentor-n6ex28xpz3tdlfghhhwbst.streamlit.app/)