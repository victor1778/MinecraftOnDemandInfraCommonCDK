import json
import os

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME")

if not TABLE_NAME:
    raise ValueError("Missing required environment variables")

sfn = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")


def lambda_handler(event, context):
    table = dynamodb.Table(TABLE_NAME)

    try:
        # Fetch the executionArn from the DynamoDB table
        response = table.get_item(
            Key={
                "id": "0",
            }
        )

        if "Item" not in response or "execution_arn" not in response["Item"]:
            raise ValueError("Execution ARN not found in DynamoDB")

        execution_arn = response["Item"]["execution_arn"]
        sfn.stop_execution(executionArn=execution_arn)

        # Update the in_progress status and remove executionArn in DynamoDB
        table.update_item(
            Key={
                "id": "0",
            },
            UpdateExpression="SET in_progress = :val1 REMOVE execution_arn",
            ExpressionAttributeValues={
                ":val1": False,
            },
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "success": "true",
                    "server_status": "STOPPING",
                }
            ),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "success": "false",
                    "error": str(e),
                }
            ),
        }
