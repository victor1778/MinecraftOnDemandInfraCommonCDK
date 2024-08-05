from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from constructs import Construct


class Workflow(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cluster,
        task_definition,
        container_definition,
        security_group
    ) -> None:
        super().__init__(scope, construct_id)

        # Policy and Dependencies
        step_function_role = iam.Role(
            self,
            "StepFunctionRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
        )

        step_function_role.add_to_policy(
            iam.PolicyStatement(
                resources=["*"],
                actions=[
                    "ecs:RunTask",
                    "ecs:StopTask",
                    "ecs:DescribeTasks",
                    "iam:PassRole",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeSecurityGroups",
                ],
            )
        )

        self.cleanup_lambda = lambda_.Function(
            self,
            "CleanupWorkflowLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("src/workflow/runtime"),
        )

        # Workflow Tasks
        run_server_task = tasks.EcsRunTask(
            self,
            "RunFargate",
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,
            cluster=cluster,
            task_definition=task_definition,
            assign_public_ip=True,
            container_overrides=[
                tasks.ContainerOverride(
                    container_definition=container_definition,
                )
            ],
            launch_target=tasks.EcsFargateLaunchTarget(
                platform_version=ecs.FargatePlatformVersion.LATEST
            ),
            security_groups=[
                security_group,
            ],
        )

        cleanup_task = tasks.LambdaInvoke(
            self,
            "InvokeCleanup",
            lambda_function=self.cleanup_lambda,
        )


        # Add Catch to handle failure and transition to Choice state
        run_server_task.add_catch(
            cleanup_task,
            errors=["States.ALL"]  # Catch all errors
        )

        # Define the state machine
        event_chain = run_server_task.next(cleanup_task)

        self.state_machine = sfn.StateMachine(
            self,
            "EcsStateMachine",
            definition_body=sfn.DefinitionBody.from_chainable(event_chain),
        )
