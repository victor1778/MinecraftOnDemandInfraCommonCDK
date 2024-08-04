import json
import os

import boto3

sfn = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ["TABLE_NAME"]

if TABLE_NAME is None:
    raise ValueError("Missing environment variable")


def lambda_handler(event, context):
    table = dynamodb.Table(TABLE_NAME)

    table.update_item(
        Key={
                "id": "0",
            },
            UpdateExpression="SET in_progress = :val1",
            ExpressionAttributeValues={
                ":val1": str(False),
            },
        )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "message": "Workflow terminated successfully",
                "step_function_in_progress ": str(False),
            }
        ),
    }
