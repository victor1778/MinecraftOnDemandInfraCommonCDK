import json
import os

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME")
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN")

if not TABLE_NAME or not STATE_MACHINE_ARN:
    raise ValueError("Missing required environment variables")

sfn = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")


def lambda_handler(event, context):
    table = dynamodb.Table(TABLE_NAME)

    try:

        response = sfn.start_execution(stateMachineArn=STATE_MACHINE_ARN)
        execution_arn = response["executionArn"]

        table.update_item(
            Key={"id": "0"},
            UpdateExpression="SET execution_arn = :execution_arn, in_progress = :new_val",
            ConditionExpression="attribute_not_exists(in_progress) OR in_progress = :false_val",
            ExpressionAttributeValues={":new_val": True, ":false_val": False, ":execution_arn": execution_arn},
            ReturnValues="UPDATED_NEW",
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "success": "true",
                    "server_status": "STARTING",
                }
            ),
        }

    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException as e:
        return {
            "statusCode": 409,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "success": "true",
                    "server_status": "ONLINE",
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
