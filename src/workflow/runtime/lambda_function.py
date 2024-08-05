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
