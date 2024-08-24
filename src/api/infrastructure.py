from aws_cdk import Duration
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_lambda as lambda_
from constructs import Construct


class API(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        dynamodb_table_name: str,
        state_machine_arn: str,
    ) -> None:
        super().__init__(scope, construct_id)

        self.launcher_lambda = lambda_.Function(
            self,
            "launcher-lambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="start_function.lambda_handler",
            code=lambda_.Code.from_asset("src/api/runtime"),
            timeout=Duration.seconds(30),
            environment={
                "TABLE_NAME": dynamodb_table_name,
                "STATE_MACHINE_ARN": state_machine_arn,
            },
        )

        self.stop_lambda = lambda_.Function(
            self,
            "stop-lambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="stop_function.lambda_handler",
            code=lambda_.Code.from_asset("src/api/runtime"),
            timeout=Duration.seconds(30),
            environment={
                "TABLE_NAME": dynamodb_table_name,
            },
        )

        api = apigw.RestApi(
            self,
            "pzcraft-api",
            rest_api_name="PZ Craft API",
            default_cors_preflight_options={
                "allow_origins": apigw.Cors.ALL_ORIGINS,
                "allow_methods": apigw.Cors.ALL_METHODS,
            },
        )

        v1_resource = api.root.add_resource("v1")

        server_resource = v1_resource.add_resource("server")
        start_resource = server_resource.add_resource("start")
        stop_resource = server_resource.add_resource("stop")

        launcher_lambda_integration = apigw.LambdaIntegration(self.launcher_lambda)
        stop_lambda_integration = apigw.LambdaIntegration(self.stop_lambda)
        
        start_resource.add_method("GET", launcher_lambda_integration)
        stop_resource.add_method("GET", stop_lambda_integration)
