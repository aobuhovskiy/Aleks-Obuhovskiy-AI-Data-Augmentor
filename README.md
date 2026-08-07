# AI Data Augmentor

## Overview

This project was created for **CAIO Assignment #3 – AI Data Augmentor**.

The goal was to take a starter spreadsheet of 50 outdoor and apparel companies and enrich the data with additional business information:

- Company location
- Customer service phone number
- Official website
- Source / verification information

The project demonstrates how AI-assisted automation can improve incomplete business data while also showing the importance of validation, source quality, and human review.

The final solution combines automated enrichment, data validation, manual quality assurance, a Streamlit user interface, and an AWS serverless cloud deployment.

---

## Project Objectives

The main objectives were to:

1. Read the original company dataset.
2. Automatically research missing company information.
3. Validate results before saving them.
4. Avoid guessing when reliable information could not be found.
5. Store uncertain values as `UNKNOWN`.
6. Produce a clean augmented Excel spreadsheet.
7. Document the approach, challenges, and lessons learned.
8. Provide a simple UI for reviewing the data.
9. Extend the project with Infrastructure as Code, NoSQL, and serverless cloud technologies.

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

### Extra Challenge – Cloud

- Terraform
- Amazon DynamoDB
- AWS Lambda
- AWS IAM
- AWS CLI
- boto3

---

## Project Structure

```text
Aleks-Obuhovskiy-AI-Data-Augmentor/
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

I kept this version because it shows the development process and how the solution changed after testing.

## 3. Prefer Official Sources

The enrichment process attempts to identify official company sources before accepting information.

The solution looks for:

- Official corporate websites
- Customer service pages
- Contact pages
- Company headquarters information
- Official support numbers

Results from retailers, unrelated businesses, regional sites, and suspicious look-alike domains were treated carefully.

## 4. Validate the Results

Automated search results were not accepted blindly.

Validation included checks for:

- Incorrect or unrelated domains
- Regional domains instead of official corporate sites
- Retailer websites
- Look-alike domains
- Incorrect phone numbers
- International phone numbers when a U.S. customer-service number was expected
- Distribution centers confused with headquarters
- Incomplete or malformed addresses

## 5. Human Quality Assurance

Automated enrichment produced useful results, but several edge cases showed that search automation alone was not reliable enough.

I therefore performed a final human QA review using official company information.

When reliable information could not be confirmed, I used `UNKNOWN` rather than guessing.

**Key lesson:** Automated enrichment can accelerate research, but high-quality business data still requires validation and clear confidence rules.

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

The Lambda successfully retrieved Patagonia from DynamoDB, including:

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

This allowed the serverless logic to be validated before creating AWS infrastructure.

---

# Data Quality and Hallucination Control

A major focus of this project was preventing incorrect information from appearing authoritative.

The following rules were used:

1. Prefer official company sources.
2. Reject unrelated or suspicious domains.
3. Validate extracted phone numbers.
4. Review questionable locations manually.
5. Preserve source information when possible.
6. Use `UNKNOWN` when confidence is insufficient.
7. Perform human QA before considering the spreadsheet final.

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
- Exception management
- Human review for ambiguous cases

I learned that an AI-enabled data enrichment solution should not simply maximize the number of populated fields. It should maximize the number of **defensible and verified fields**.

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

The project started as a spreadsheet enrichment exercise and evolved into a complete AI-assisted data workflow.

```text
Search
  ↓
Extraction
  ↓
Validation
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
```

The most important lesson was that successful AI automation is not only about generating results. It is also about creating controls that determine when the system should trust a result, reject it, or clearly return `UNKNOWN`.

---

## Author

**Aleks Obuhovskiy**

CAIO Assignment #3 – AI Data Augmentor
