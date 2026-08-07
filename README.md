# Aleks Obuhovskiy - AI Data Augmentor

## Project Overview

This project augments a starter list of 50 apparel and outdoor companies with:

- Company location
- Customer-service phone number
- Official website
- Source references used during validation

The project was created for Assignment #3: **AI Data Augmentor**.

## Repository

GitHub repository:

https://github.com/aobuhovskiy/Aleks-Obuhovskiy-AI-Data-Augmentor

## Approach

The Python workflow performs a first-pass automated enrichment using:

1. **DDGS web search** to discover likely official company sources.
2. **Domain validation** to reject retailers, social media, directories, regional duplicates, and suspicious look-alike sites.
3. **Direct official-site retrieval** with `requests` and `BeautifulSoup`.
4. **Phone extraction and ranking** that prefers customer-service/customer-care numbers and penalizes warranty, store, fax, media, or unrelated numbers.
5. **Location extraction** using headquarters/corporate-address language and structured page data.
6. **Caching and retries** to reduce repeated searches and make reruns safer.
7. **UNKNOWN fallback** when a value cannot be verified reliably.

## Human QA

Automated web augmentation is not perfect. During testing, several edge cases appeared:

- Regional domains were sometimes ranked above the primary site.
- Retailer/look-alike sites appeared for some brands.
- A warranty or international number could be mistaken for U.S. customer service.
- Distribution centers or office addresses could be mistaken for headquarters.
- Search snippets sometimes lacked enough context to verify a field.

The final spreadsheet therefore includes a **manual QA review**. Values were corrected when official company sources provided stronger evidence. When reliable evidence was still unavailable, the value was intentionally left as `UNKNOWN` instead of guessing.

This manual review is part of the quality-control process rather than an attempt to hide automation errors.

## Project Structure

```text
Aleks-Obuhovskiy-AI-Data-Augmentor/
├── app.py
├── data/
│   └── starter-companies.csv
├── output/
│   └── augmented-companies.xlsx
├── reflection/
│   └── Aleks_Obuhovskiy_AI_Data_Augmentor_Reflection.pdf
├── src/
│   ├── augment_companies.py
│   └── augment_companies_Tavily.py   # optional earlier prototype
├── requirements.txt
└── README.md
```

## Setup

Python 3.10+ is recommended.

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

From the repository root:

```bash
python src/augment_companies.py
```

The script writes the result to:

```text
output/augmented-companies.xlsx
```

A local search cache may also be created at:

```text
data/ddgs_cache.json
```

## Streamlit UI

The repository includes a simple Streamlit interface as an optional challenge feature.

Start the UI from the repository root:

```bash
streamlit run app.py
```

The UI provides three views:

- **Final Dataset** - browse, filter, and download the validated 50-company spreadsheet.
- **Try the Agent** - upload a CSV and run a small live demo on up to 5 selected companies.
- **How It Works** - review the augmentation and QA workflow.

The 5-company live limit is intentional. It keeps the classroom demo responsive while the full 50-company result remains available as the validated submission dataset.

## Data Quality Rules

- Prefer the company's primary official website.
- Reject third-party retailers, directories, and suspicious look-alike domains.
- Prefer customer-service/customer-care phone numbers.
- Do not treat warranty, fax, press, or unrelated international phone numbers as the primary support number.
- Prefer explicit headquarters or corporate-location evidence.
- Do not guess.
- Use `UNKNOWN` when the available evidence is insufficient.

## Tools Used

- Python
- pandas / openpyxl
- DDGS
- requests
- BeautifulSoup
- phonenumbers
- VS Code
- Git / GitHub
- Streamlit

## Final Deliverables

- `output/augmented-companies.xlsx` - completed augmented dataset
- `reflection/Aleks_Obuhovskiy_AI_Data_Augmentor_Reflection.pdf` - one-page reflection
- GitHub repository containing the source code and documentation
