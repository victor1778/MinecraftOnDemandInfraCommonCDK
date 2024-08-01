from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_efs as efs
from aws_cdk import aws_iam as iam
from constructs import Construct


class MinecraftOnDemandInfraCommonCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(
            self,
            "VPC",
            max_azs=3,
            nat_gateways=0,
        )

        fileSystem = efs.FileSystem(
            self,
            "FileSystem",
            vpc=vpc,
            removal_policy=RemovalPolicy.DESTROY,
        )

        access_point = efs.AccessPoint(
            self,
            "AccessPoint",
            file_system=fileSystem,
            path="/minecraft",
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
                    actions=[
                        "elasticfilesystem:ClientMount",
                        "elasticfilesystem:ClientWrite",
                        "elasticfilesystem:DescribeFileSystems",
                    ],
                    resources=[fileSystem.file_system_arn],
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

        # Create an ECS cluster
        cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=vpc,
            container_insights=True,
            enable_fargate_capacity_providers=True,
        )

        task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDefinition",
            runtime_platform=ecs.RuntimePlatform(
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
                cpu_architecture=ecs.CpuArchitecture.ARM64,
            ),
            memory_limit_mib=4096,
            cpu=2,
            volumes=[
                ecs.Volume(
                    name="efsVolume",
                    efs_volume_configuration=ecs.EfsVolumeConfiguration(
                        file_system_id=fileSystem.file_system_id,
                        transit_encryption="ENABLED",
                        authorization_config=ecs.AuthorizationConfig(
                            access_point_id=access_point.access_point_id,
                            iam="ENABLED",
                        ),
                    ),
                ),
            ],
        )
