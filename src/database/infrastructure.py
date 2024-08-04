from aws_cdk import RemovalPolicy
from aws_cdk import aws_dynamodb as dynamodb
from constructs import Construct


class Database(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        dynamodb_billing_mode: dynamodb.BillingMode,
    ) -> None:
        super().__init__(scope, construct_id)

        self.dynamodb_table = dynamodb.Table(
            self,
            "sfn-state-table",
            billing_mode=dynamodb_billing_mode,
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING,
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )
