import json
import os

import boto3
from boto3.dynamodb.conditions import Key

sfn = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ["TABLE_NAME"]
STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]

if TABLE_NAME is None:
    raise ValueError("Missing environment variable")


def lambda_handler(event, context):
    table = dynamodb.Table(TABLE_NAME)

    response = table.query(
        KeyConditionExpression=Key("id").eq("0"),
    )

    in_progress = False
    items = response["Items"]

    if items:
        in_progress = True if items[0]["in_progress"] == "True" else False

    if not in_progress:
        sfn.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
        )

        table.update_item(
            Key={
                "id": "0",
            },
            UpdateExpression="SET in_progress = :val1",
            ExpressionAttributeValues={
                ":val1": str(True),
            },
        )

        return {
            "statusCode": 202,
            "headers": {
                "Content-Type": "application/json",
                "Retry-After": "60",
            },
            "body": json.dumps(
                {
                    "message": "Workflow execution started",
                    "server_status": str(False),
                    "step_function_in_progress ": str(True),
                }
            ),
        }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "message": "Workflow already in progress",
                "server_status": str(True),
                "step_function_in_progress ": str(in_progress),
            }
        ),
    }
