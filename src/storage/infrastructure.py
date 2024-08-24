import os

from aws_cdk import RemovalPolicy
from aws_cdk import aws_datasync as datasync
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_efs as efs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct

from src.network.infrastructure import Network


class Storage(Construct):

    def __init__(self, scope: Construct, construct_id: str, network: Network) -> None:
        super().__init__(scope, construct_id)

        self.file_system = efs.FileSystem(
            self,
            "FileSystem",
            vpc=network.vpc,
            security_group=network.security_group,
            removal_policy=RemovalPolicy.DESTROY,
            throughput_mode=efs.ThroughputMode.ELASTIC,
            enable_automatic_backups=True,
        )

        self.access_point = efs.AccessPoint(
            self,
            "AccessPoint",
            file_system=self.file_system,
            path="/data",
            posix_user=efs.PosixUser(
                uid="1000",
                gid="1000",
            ),
            create_acl=efs.Acl(
                owner_gid="1000",
                owner_uid="1000",
                permissions="0777",
            ),
        )

        self.efs_read_write_policy = iam.Policy(
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
                        self.file_system.file_system_arn,
                    ],
                    conditions={
                        "StringEquals": {
                            "elasticfilesystem:AccessPointArn": self.access_point.access_point_arn
                        }
                    },
                ),
            ],
        )
