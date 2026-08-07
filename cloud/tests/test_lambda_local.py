import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lambda"))


class FakeTable:
    def __init__(self):
        self.items = {
            "Patagonia": {
                "company_name": "Patagonia",
                "location": "Ventura, California",
                "phone": "800-638-6464",
                "website": "https://www.patagonia.com",
            },
            "Garmin": {
                "company_name": "Garmin",
                "location": "Olathe, Kansas",
                "phone": "800-800-1020",
                "website": "https://www.garmin.com",
            },
        }

    def get_item(self, Key):
        item = self.items.get(Key["company_name"])
        return {"Item": item} if item else {}

    def scan(self, **kwargs):
        return {"Items": list(self.items.values())}


fake_table = FakeTable()
fake_dynamodb = MagicMock()
fake_dynamodb.Table.return_value = fake_table


with patch("boto3.resource", return_value=fake_dynamodb):
    import lambda_function

    lambda_function.table = fake_table

    health = lambda_function.lambda_handler(
        {"action": "health"},
        None,
    )
    assert health["statusCode"] == 200

    get_result = lambda_function.lambda_handler(
        {
            "action": "get",
            "company_name": "Patagonia",
        },
        None,
    )
    get_body = json.loads(get_result["body"])
    assert get_result["statusCode"] == 200
    assert get_body["location"] == "Ventura, California"

    missing = lambda_function.lambda_handler(
        {
            "action": "get",
            "company_name": "Not A Company",
        },
        None,
    )
    assert missing["statusCode"] == 404

    listed = lambda_function.lambda_handler(
        {"action": "list"},
        None,
    )
    listed_body = json.loads(listed["body"])
    assert listed["statusCode"] == 200
    assert listed_body["count"] == 2
    assert listed_body["items"][0]["company_name"] == "Garmin"
    assert listed_body["items"][1]["company_name"] == "Patagonia"

print("PASS: Lambda local tests")
