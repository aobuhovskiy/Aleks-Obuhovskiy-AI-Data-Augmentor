import json
import os
from decimal import Decimal

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "ai-data-augmentor-companies")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def _parse_event(event):
    """
    Supports both direct Lambda test events and API-style events.

    Direct examples:
      {"action": "list"}
      {"action": "get", "company_name": "Patagonia"}
      {"action": "health"}

    API-style examples:
      queryStringParameters={"company_name":"Patagonia"}
    """
    if not isinstance(event, dict):
        return "list", None

    action = event.get("action")
    company_name = event.get("company_name")

    if action:
        return str(action).lower(), company_name

    qs = event.get("queryStringParameters") or {}
    if qs.get("company_name"):
        return "get", qs.get("company_name")

    return "list", None


def lambda_handler(event, context):
    action, company_name = _parse_event(event)

    if action == "health":
        return _response(
            200,
            {
                "status": "ok",
                "service": "AI Data Augmentor",
                "table": TABLE_NAME,
            },
        )

    if action == "get":
        if not company_name:
            return _response(
                400,
                {"error": "company_name is required for action=get"},
            )

        result = table.get_item(
            Key={"company_name": company_name}
        )

        item = result.get("Item")

        if not item:
            return _response(
                404,
                {
                    "error": "Company not found",
                    "company_name": company_name,
                },
            )

        return _response(200, item)

    if action == "list":
        items = []
        scan_kwargs = {}

        while True:
            result = table.scan(**scan_kwargs)
            items.extend(result.get("Items", []))

            last_key = result.get("LastEvaluatedKey")
            if not last_key:
                break

            scan_kwargs["ExclusiveStartKey"] = last_key

        items.sort(
            key=lambda item: str(
                item.get("company_name", "")
            ).lower()
        )

        return _response(
            200,
            {
                "count": len(items),
                "items": items,
            },
        )

    return _response(
        400,
        {
            "error": "Unsupported action",
            "supported_actions": [
                "health",
                "list",
                "get",
            ],
        },
    )
