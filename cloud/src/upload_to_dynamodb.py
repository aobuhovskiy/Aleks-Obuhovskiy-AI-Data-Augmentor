import argparse
import os
from pathlib import Path

import boto3
import pandas as pd


DEFAULT_FILE = Path("output/augmented-companies.xlsx")
DEFAULT_TABLE = "ai-data-augmentor-companies"


def clean_value(value):
    if pd.isna(value):
        return "UNKNOWN"

    text = str(value).strip()
    return text if text else "UNKNOWN"


def load_records(path):
    df = pd.read_excel(path)

    required = {
        "company_name",
        "Location",
        "Phone",
        "Website",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            "Spreadsheet is missing required columns: "
            + ", ".join(sorted(missing))
        )

    records = []

    for _, row in df.iterrows():
        record = {
            "company_name": clean_value(row["company_name"]),
            "location": clean_value(row["Location"]),
            "phone": clean_value(row["Phone"]),
            "website": clean_value(row["Website"]),
        }

        if "Source" in df.columns:
            record["source"] = clean_value(row["Source"])

        records.append(record)

    return records


def upload_records(records, table_name, region=None):
    session = boto3.Session(region_name=region)
    dynamodb = session.resource("dynamodb")
    table = dynamodb.Table(table_name)

    print(f"Uploading {len(records)} records to {table_name}...")

    with table.batch_writer(
        overwrite_by_pkeys=["company_name"]
    ) as batch:
        for record in records:
            batch.put_item(Item=record)

    print("Upload complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Upload final AI Data Augmentor results to DynamoDB."
    )

    parser.add_argument(
        "--file",
        default=str(DEFAULT_FILE),
        help="Path to augmented-companies.xlsx",
    )

    parser.add_argument(
        "--table",
        default=os.getenv(
            "DYNAMODB_TABLE",
            DEFAULT_TABLE,
        ),
        help="DynamoDB table name",
    )

    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION"),
        help="AWS region, for example us-east-1",
    )

    args = parser.parse_args()

    records = load_records(
        Path(args.file)
    )

    upload_records(
        records,
        args.table,
        args.region,
    )


if __name__ == "__main__":
    main()
