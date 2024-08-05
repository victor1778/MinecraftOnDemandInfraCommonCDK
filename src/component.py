from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_efs as efs
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_lambda_event_sources as lambda_event_sources
from aws_cdk import aws_logs as logs
from aws_cdk import aws_sns as sns
from constructs import Construct

from constants import (
    CLUSTER_NAME,
    DOMAIN_NAME,
    ECS_VOLUME_NAME,
    JAVA_EDITION_DOCKER_IMAGE,
    MC_SERVER_CONTAINER_NAME,
    MODPACK,
    WORLD,
)
from src.api.infrastructure import API
from src.database.infrastructure import Database
from src.domain.infrastructure import Domain
from src.workflow.infrastructure import Workflow


class MinecraftOnDemandInfraCommonCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        domain = Domain(
            self,
            "Network",
        )

        """
        ******************************
        *     MC Server Construct    *
        ******************************
        """

        vpc = ec2.Vpc(
            self,
            "VPC",
            max_azs=3,
        )

        security_group = ec2.SecurityGroup(
            self,
            "ServiceSecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            description="Security group for Minecraft server",
        )

        security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(25565),
        )

        security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(2049),
            description="Allow NFS traffic",
        )

        file_system = efs.FileSystem(
            self,
            "FileSystem",
            vpc=vpc,
            security_group=security_group,
            removal_policy=RemovalPolicy.DESTROY,
        )

        access_point = efs.AccessPoint(
            self,
            "AccessPoint",
            file_system=file_system,
            path="/data",
            posix_user=efs.PosixUser(
                uid="1000",
                gid="1000",
            ),
            create_acl=efs.Acl(
                owner_gid="1000",
                owner_uid="1000",
                permissions="0755",
            ),
        )

        efs_read_write_policy = iam.Policy(
            self,
            "EfsReadWritePolicy",
            statements=[
                iam.PolicyStatement(
                    sid="AllowReadWriteOnEFS",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "elasticfilesystem:ClientMount",
                        "elasticfilesystem:ClientWrite",
                        "elasticfilesystem:DescribeFileSystems",
                    ],
                    resources=[
                        file_system.file_system_arn,
                    ],
                    conditions={
                        "StringEquals": {
                            "elasticfilesystem:AccessPointArn": access_point.access_point_arn
                        }
                    },
                ),
            ],
        )

        ecs_task_role = iam.Role(
            self,
            "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Role for Minecraft ECS task",
        )

        efs_read_write_policy.attach_to_role(ecs_task_role)

        cluster = ecs.Cluster(
            self,
            CLUSTER_NAME,
            vpc=vpc,
            container_insights=True,
        )

        # Create an ECS task definition
        task_definition = ecs.TaskDefinition(
            self,
            "TaskDefinition",
            runtime_platform=ecs.RuntimePlatform(
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
                cpu_architecture=ecs.CpuArchitecture.ARM64,
            ),
            compatibility=ecs.Compatibility.FARGATE,
            task_role=ecs_task_role,
            memory_mib="8192",
            cpu="4096",
        )

        task_definition.add_volume(
            name=ECS_VOLUME_NAME,
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=file_system.file_system_id,
                transit_encryption="ENABLED",
                authorization_config=ecs.AuthorizationConfig(
                    access_point_id=access_point.access_point_id,
                    iam="ENABLED",
                ),
            ),
        )

        # Create an ECS container definition
        container_definition = task_definition.add_container(
            MC_SERVER_CONTAINER_NAME,
            image=ecs.ContainerImage.from_registry(JAVA_EDITION_DOCKER_IMAGE),
            port_mappings=[
                ecs.PortMapping(
                    container_port=25565,
                    host_port=25565,
                    protocol=ecs.Protocol.TCP,
                ),
            ],
            environment={
                "EULA": "TRUE",
                "MAX_MEMORY": "4G",
                "VERSION": "1.20.1",
                "TYPE": "FABRIC",
                "FABRIC_LOADER_VERSION": "0.15.9",
                "WORLD": WORLD,
                "MODPACK": MODPACK,
                "FABRIC_LOADER_VERSION": "0.15.9",
                "MOTD": "A §nPZ§r server. Powered by §3Docker§r and §6AWS§r",
                "OPS": "Viktor1778",
                "ENABLE_AUTOSTOP": "TRUE",
                "AUTOSTOP_TIMEOUT_INIT": "600",
                "AUTOSTOP_TIMEOUT_EST": "600",
                "ALLOW_FLIGHT": "TRUE",
                "DIFFICULTY": "normal",
                "LEVEL_TYPE": "minecraft:large_biomes",
                "NETWORK_COMPRESSION_THRESHOLD": "512",
                "VIEW_DISTANCE": "10",
                "SIMULATION_DISTANCE": "4",
                "SYNC_CHUNK_WRITES": "FALSE",
            },
            logging=ecs.AwsLogDriver(
                log_retention=logs.RetentionDays.THREE_DAYS,
                stream_prefix=MC_SERVER_CONTAINER_NAME,
            ),
        )

        container_definition.add_mount_points(
            ecs.MountPoint(
                container_path="/data",
                source_volume=ECS_VOLUME_NAME,
                read_only=False,
            )
        )

        ecs_task_running_topic = sns.Topic(
            self, "EcsTaskRunningTopic", display_name="ECS Task Running Topic"
        )

        ecs_task_running_rule = events.Rule(
            self,
            "ECSTaskRunningRule",
            event_pattern=events.EventPattern(
                source=["aws.ecs"],
                detail_type=["ECS Task State Change"],
                detail={
                    "lastStatus": ["RUNNING"],
                    "clusterArn": [cluster.cluster_arn],
                    "taskDefinitionArn": [task_definition.task_definition_arn],
                },
            ),
        )

        ecs_task_running_rule.add_target(targets.SnsTopic(ecs_task_running_topic))

        ecs_task_running_topic.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sns:Publish"],
                principals=[iam.ServicePrincipal("events.amazonaws.com")],
                resources=[ecs_task_running_topic.topic_arn],
            )
        )

        upsert_record_lambda = lambda_.Function(
            self,
            "UpsertRecordLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("./src/lambda/upsert_record"),
            environment={
                "DOMAIN_NAME": DOMAIN_NAME,
                "HOSTED_ZONE_ID": domain.hosted_zone.hosted_zone_id,
            },
        )

        upsert_record_lambda.add_event_source(
            lambda_event_sources.SnsEventSource(ecs_task_running_topic)
        )

        ecs_task_running_topic.grant_publish(upsert_record_lambda)

        upsert_record_lambda.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=[
                    "ecs:DescribeTasks",
                    "ec2:DescribeNetworkInterfaces",
                ],
                resources=["*"],
            )
        )

        upsert_record_lambda.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=[
                    "route53:ChangeResourceRecordSets",
                ],
                resources=[
                    f"arn:aws:route53:::hostedzone/{domain.hosted_zone.hosted_zone_id}",
                ],
            )
        )

        workflow = Workflow(
            self,
            "Workflow",
            cluster=cluster,
            task_definition=task_definition,
            container_definition=container_definition,
            security_group=security_group,
        )

        database = Database(
            self,
            "Database",
            dynamodb_billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        workflow.cleanup_lambda.add_environment(
            "TABLE_NAME",
            database.dynamodb_table.table_name,
        )

        api = API(
            self,
            "API",
            dynamodb_table_name=database.dynamodb_table.table_name,
            state_machine_arn=workflow.state_machine.state_machine_arn,
        )

        database.dynamodb_table.grant_read_write_data(api.launcher_lambda)
        database.dynamodb_table.grant_read_write_data(workflow.cleanup_lambda)
        workflow.state_machine.grant_start_execution(api.launcher_lambda)
