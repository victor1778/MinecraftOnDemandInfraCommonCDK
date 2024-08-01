from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_efs as efs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from constructs import Construct

from constants import (
    CLUSTER_NAME,
    ECS_VOLUME_NAME,
    JAVA_EDITION_DOCKER_IMAGE,
    MC_SERVER_CONTAINER_NAME,
    SERVICE_NAME,
)


class MinecraftOnDemandInfraCommonCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a VPC
        vpc = ec2.Vpc(
            self,
            "VPC",
            max_azs=3,
            nat_gateways=0,
        )

        # Create an EFS file system
        file_system = efs.FileSystem(
            self,
            "FileSystem",
            vpc=vpc,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Create an EFS access point
        access_point = efs.AccessPoint(
            self,
            "AccessPoint",
            file_system=file_system,
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

        # Create an IAM policy for ECS task role
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

        # Create an IAM role for ECS task
        ecs_task_role = iam.Role(
            self,
            "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Role for Minecraft ECS task",
        )

        # Attach the EFS read-write policy to the ECS task role
        efs_read_write_policy.attach_to_role(ecs_task_role)

        # Create an ECS cluster
        cluster = ecs.Cluster(
            self,
            CLUSTER_NAME,
            vpc=vpc,
            container_insights=True,
            enable_fargate_capacity_providers=True,
        )

        # Create an ECS task definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDefinition",
            runtime_platform=ecs.RuntimePlatform(
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
                cpu_architecture=ecs.CpuArchitecture.ARM64,
            ),
            task_role=ecs_task_role,
            memory_limit_mib=4096,
            cpu=2048,
            volumes=[
                ecs.Volume(
                    name=ECS_VOLUME_NAME,
                    efs_volume_configuration=ecs.EfsVolumeConfiguration(
                        file_system_id=file_system.file_system_id,
                        transit_encryption="ENABLED",
                        authorization_config=ecs.AuthorizationConfig(
                            access_point_id=access_point.access_point_id,
                            iam="ENABLED",
                        ),
                    ),
                ),
            ],
        )

        # Create an ECS container definition
        container = ecs.ContainerDefinition(
            self,
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
                "MOTD": "A §nPerroZompopo§r server. Powered by §3Docker§r and §6AWS§r",
                "OPS": "Viktor1778",
            },
            essential=True,
            task_definition=task_definition,
            logging=ecs.AwsLogDriver(
                log_retention=logs.RetentionDays.THREE_DAYS,
                stream_prefix=MC_SERVER_CONTAINER_NAME,
            ),
        )

        # Add a mount point to the container
        container.add_mount_points(
            ecs.MountPoint(
                container_path="/data",
                source_volume=ECS_VOLUME_NAME,
                read_only=False,
            )
        )

        # Create a security group for the service
        service_security_group = ec2.SecurityGroup(
            self,
            "ServiceSecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            description="Security group for Minecraft service",
        )

        # Add an ingress rule to the security group
        service_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(25565),  # IngressRulePort
        )

        # Create an ECS service
        minecraft_server_service = ecs.FargateService(
            self,
            "FargateService",
            cluster=cluster,
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE",
                    weight=1,
                    base=1,
                ),
            ],
            task_definition=task_definition,
            platform_version=ecs.FargatePlatformVersion.LATEST,
            service_name=SERVICE_NAME,
            desired_count=1,
            assign_public_ip=True,
            security_groups=[
                service_security_group,
            ],
        )

        # Allow the service to connect to the file system
        file_system.connections.allow_default_port_from(
            minecraft_server_service.connections,
        )
