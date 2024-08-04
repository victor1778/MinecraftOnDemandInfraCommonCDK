import json
import os

import boto3

ecs = boto3.client("ecs")
ec2 = boto3.client("ec2")
route53 = boto3.client("route53")

HOSTED_ZONE_ID = os.environ.get("HOSTED_ZONE_ID")
DOMAIN_NAME = os.environ.get("DOMAIN_NAME")


def lambda_handler(event, context):
    # Extract task ARN from SNS message
    message = json.loads(event["Records"][0]["Sns"]["Message"])
    task_arn = message["detail"]["taskArn"]
    cluster_arn = message["detail"]["clusterArn"]

    # Describe the task to get the public IP
    response = ecs.describe_tasks(cluster=cluster_arn, tasks=[task_arn])
    task = response["tasks"][0]
    eni_id = next(
        detail["value"]
        for detail in task["attachments"][0]["details"]
        if detail["name"] == "networkInterfaceId"
    )

    public_ip = ec2.describe_network_interfaces(NetworkInterfaceIds=[eni_id])[
        "NetworkInterfaces"
    ][0]["Association"]["PublicIp"]

    route53.change_resource_record_sets(
        HostedZoneId=HOSTED_ZONE_ID,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": DOMAIN_NAME,
                        "Type": "A",
                        "TTL": 30,
                        "ResourceRecords": [{"Value": public_ip}],
                    },
                }
            ]
        },
    )

    return {
        "statusCode": 200,
        "body": json.dumps(f"A record updated successfully. IP: {public_ip}"),
    }
